# backend/admin_db_service.py
import re
import pandas as pd
from sqlalchemy import create_engine, text, inspect


def is_blank(x):
    return x is None or str(x).strip() == ""


class AdminDBError(Exception):
    pass


class MySQLAdminService:
    @staticmethod
    def _validate_identifier(name: str) -> str:
        if not name or not re.fullmatch(r"[A-Za-z0-9_]+", name):
            raise AdminDBError(f"Identifier không hợp lệ: {name}")
        return name

    @staticmethod
    def make_engine(host: str, port: int, user: str, password: str, db: str = None):
        if db:
            db = MySQLAdminService._validate_identifier(db)
            url = "mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8mb4".format(
                user, password, host, port, db
            )
        else:
            url = "mysql+pymysql://{}:{}@{}:{}/?charset=utf8mb4".format(
                user, password, host, port
            )
        return create_engine(url)

    @staticmethod
    def list_databases(host: str, port: int, user: str, password: str):
        try:
            engine = MySQLAdminService.make_engine(host, port, user, password, db=None)
            with engine.connect() as conn:
                rows = conn.execute(text("SHOW DATABASES")).fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            raise AdminDBError(str(e))

    @staticmethod
    def list_tables(host: str, port: int, user: str, password: str, database: str):
        try:
            database = MySQLAdminService._validate_identifier(database)
            engine = MySQLAdminService.make_engine(host, port, user, password, db=database)
            with engine.connect() as conn:
                rows = conn.execute(text("SHOW TABLES")).fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            raise AdminDBError(str(e))

    @staticmethod
    def load_table(host: str, port: int, user: str, password: str, database: str, table: str):
        try:
            database = MySQLAdminService._validate_identifier(database)
            table = MySQLAdminService._validate_identifier(table)

            engine = MySQLAdminService.make_engine(host, port, user, password, db=database)
            insp = inspect(engine)

            pk_info = insp.get_pk_constraint(table)
            pk_cols = pk_info.get("constrained_columns", []) or []
            auto_inc_pk = (len(pk_cols) == 1 and pk_cols[0].lower() == "id")

            df = pd.read_sql("SELECT * FROM `{}`".format(table), engine)

            rows = []
            for _, row in df.iterrows():
                row_dict = {}
                for col in df.columns:
                    val = row[col]
                    if pd.isna(val):
                        row_dict[col] = ""
                    else:
                        row_dict[col] = val.item() if hasattr(val, "item") else val
                rows.append(row_dict)

            return {
                "table": table,
                "pk_cols": pk_cols,
                "auto_inc_pk": auto_inc_pk,
                "columns": [str(c) for c in df.columns],
                "rows": rows,
            }
        except Exception as e:
            raise AdminDBError(str(e))

    @staticmethod
    def save_table(host: str, port: int, user: str, password: str, database: str, table: str, rows: list):
        try:
            database = MySQLAdminService._validate_identifier(database)
            table = MySQLAdminService._validate_identifier(table)

            engine = MySQLAdminService.make_engine(host, port, user, password, db=database)
            insp = inspect(engine)

            pk_info = insp.get_pk_constraint(table)
            pk_cols = pk_info.get("constrained_columns", []) or []
            auto_inc_pk = (len(pk_cols) == 1 and pk_cols[0].lower() == "id")

            if not pk_cols:
                raise AdminDBError(
                    "Table này không có PRIMARY KEY. "
                    "Để update/delete an toàn, hãy thêm PK trước."
                )

            df_original = pd.read_sql("SELECT * FROM `{}`".format(table), engine)
            original_columns = [str(c) for c in df_original.columns]

            if rows:
                df_new = pd.DataFrame(rows)
            else:
                df_new = pd.DataFrame(columns=original_columns)

            # Đồng bộ cột theo DB gốc
            for col in original_columns:
                if col not in df_new.columns:
                    df_new[col] = ""

            df_new = df_new[original_columns]

            def pk_key_from_row(row_dict):
                key = []
                for pk in pk_cols:
                    val = row_dict.get(pk, "")
                    if val is None:
                        val = ""
                    key.append(str(val).strip())
                return tuple(key)

            orig_map = {}
            for _, row in df_original.iterrows():
                row_dict = row.to_dict()
                orig_map[pk_key_from_row(row_dict)] = row_dict

            new_map = {}
            new_rows_no_pk = []

            for _, row in df_new.iterrows():
                row_dict = row.to_dict()
                k = pk_key_from_row(row_dict)

                if auto_inc_pk and len(pk_cols) == 1 and is_blank(k[0]):
                    new_rows_no_pk.append(row_dict)
                else:
                    if k in new_map:
                        raise AdminDBError(f"Duplicate PRIMARY KEY trong dữ liệu gửi lên: {k}")
                    new_map[k] = row_dict

            orig_keys = set(orig_map.keys())
            new_keys = set(new_map.keys())

            delete_keys = list(orig_keys - new_keys)
            insert_keys = list(new_keys - orig_keys)
            common_keys = list(orig_keys & new_keys)

            update_keys = []
            for k in common_keys:
                old_row = orig_map[k]
                new_row = new_map[k]
                changed = False

                for col in original_columns:
                    if col in pk_cols:
                        continue

                    ov = "" if old_row.get(col) is None else str(old_row.get(col))
                    nv = "" if new_row.get(col) is None else str(new_row.get(col))

                    if ov != nv:
                        changed = True
                        break

                if changed:
                    update_keys.append(k)

            with engine.begin() as conn:
                # DELETE
                for k in delete_keys:
                    where_clause = " AND ".join(
                        ["`{}`=:pk_{}".format(pk, i) for i, pk in enumerate(pk_cols)]
                    )
                    params = {"pk_{}".format(i): k[i] for i in range(len(pk_cols))}
                    sql = "DELETE FROM `{}` WHERE {}".format(table, where_clause)
                    conn.execute(text(sql), params)

                # INSERT có PK rõ ràng
                for k in insert_keys:
                    row_dict = new_map[k]
                    cols = list(original_columns)

                    col_clause = ", ".join(["`{}`".format(c) for c in cols])
                    val_clause = ", ".join([":{}".format(c) for c in cols])

                    sql = "INSERT INTO `{}` ({}) VALUES ({})".format(
                        table, col_clause, val_clause
                    )
                    conn.execute(text(sql), row_dict)

                # INSERT auto-inc PK trống
                for row_dict in new_rows_no_pk:
                    cols = [c for c in original_columns if c not in pk_cols]
                    col_clause = ", ".join(["`{}`".format(c) for c in cols])
                    val_clause = ", ".join([":{}".format(c) for c in cols])

                    params = {c: row_dict.get(c) for c in cols}

                    sql = "INSERT INTO `{}` ({}) VALUES ({})".format(
                        table, col_clause, val_clause
                    )
                    conn.execute(text(sql), params)

                # UPDATE
                for k in update_keys:
                    row_dict = new_map[k]
                    set_cols = [c for c in original_columns if c not in pk_cols]

                    if not set_cols:
                        continue

                    set_clause = ", ".join(["`{}`=:{}".format(c, c) for c in set_cols])
                    where_clause = " AND ".join(
                        ["`{}`=:pk_{}".format(pk, i) for i, pk in enumerate(pk_cols)]
                    )

                    params = {c: row_dict.get(c) for c in set_cols}
                    params.update({"pk_{}".format(i): k[i] for i in range(len(pk_cols))})

                    sql = "UPDATE `{}` SET {} WHERE {}".format(
                        table, set_clause, where_clause
                    )
                    conn.execute(text(sql), params)

            return {
                "deleted": len(delete_keys),
                "inserted": len(insert_keys) + len(new_rows_no_pk),
                "updated": len(update_keys),
            }

        except AdminDBError:
            raise
        except Exception as e:
            raise AdminDBError(str(e))