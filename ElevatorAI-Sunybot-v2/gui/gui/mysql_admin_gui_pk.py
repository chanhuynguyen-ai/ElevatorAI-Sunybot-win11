import sys
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QListWidget, QTableView, QMessageBox,
    QComboBox, QSpinBox, QAbstractItemView
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt


def is_blank(x):
    return x is None or str(x).strip() == ""


class MySQLAdminGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MySQL Table Manager (PK-safe) - PyQt5")
        self.resize(1150, 680)

        self.engine = None
        self.current_db = None
        self.current_table = None

        self.pk_cols = []
        self.auto_inc_pk = False
        self.df_original = pd.DataFrame()

        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)

        left = QVBoxLayout()
        form = QFormLayout()

        self.host_inp = QLineEdit("localhost")

        self.port_inp = QSpinBox()
        self.port_inp.setRange(1, 65535)
        self.port_inp.setValue(3306)

        self.user_inp = QLineEdit("elevator_ai")

        self.pass_inp = QLineEdit("elevator123")
        self.pass_inp.setEchoMode(QLineEdit.Password)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_mysql)

        self.db_combo = QComboBox()

        self.use_db_btn = QPushButton("Use Database")
        self.use_db_btn.clicked.connect(self.use_database)

        form.addRow("Host", self.host_inp)
        form.addRow("Port", self.port_inp)
        form.addRow("User", self.user_inp)
        form.addRow("Password", self.pass_inp)
        form.addRow(self.connect_btn)
        form.addRow(QLabel("Databases"))
        form.addRow(self.db_combo)
        form.addRow(self.use_db_btn)

        left.addLayout(form)

        left.addWidget(QLabel("Tables"))
        self.table_list = QListWidget()
        left.addWidget(self.table_list)

        self.load_table_btn = QPushButton("Load Table")
        self.load_table_btn.clicked.connect(self.load_table)
        left.addWidget(self.load_table_btn)

        root.addLayout(left, 1)

        right = QVBoxLayout()

        self.table_view = QTableView()
        self.model = QStandardItemModel()
        self.table_view.setModel(self.model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        right.addWidget(self.table_view, 1)

        actions = QHBoxLayout()

        self.add_btn = QPushButton("Add Row")
        self.del_btn = QPushButton("Delete Selected")
        self.save_btn = QPushButton("Save Changes")
        self.refresh_btn = QPushButton("Refresh")

        self.add_btn.clicked.connect(self.add_row)
        self.del_btn.clicked.connect(self.delete_selected)
        self.save_btn.clicked.connect(self.save_changes)
        self.refresh_btn.clicked.connect(self.refresh_table)

        actions.addWidget(self.add_btn)
        actions.addWidget(self.del_btn)
        actions.addWidget(self.save_btn)
        actions.addWidget(self.refresh_btn)

        right.addLayout(actions)
        root.addLayout(right, 3)

    def _make_engine(self, db=None):
        host = self.host_inp.text().strip()
        port = self.port_inp.value()
        user = self.user_inp.text().strip()
        password = self.pass_inp.text()

        if db:
            url = "mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8mb4".format(
                user, password, host, port, db
            )
        else:
            url = "mysql+pymysql://{}:{}@{}:{}/?charset=utf8mb4".format(
                user, password, host, port
            )

        return create_engine(url)
    def connect_mysql(self):
        try:
            self.engine = self._make_engine(db=None)

            with self.engine.connect() as conn:
                rows = conn.execute(text("SHOW DATABASES")).fetchall()

            self.db_combo.clear()
            for row in rows:
                self.db_combo.addItem(row[0])

            QMessageBox.information(self, "OK", "Connected. Databases loaded.")
        except Exception as e:
            self.engine = None
            QMessageBox.critical(self, "Connect failed", str(e))

    def use_database(self):
        if not self.engine:
            QMessageBox.warning(self, "Warning", "Connect first!")
            return

        db = self.db_combo.currentText().strip()
        if not db:
            QMessageBox.warning(self, "Warning", "Please choose a database.")
            return

        try:
            self.engine = self._make_engine(db=db)
            self.current_db = db
            self.current_table = None
            self.pk_cols = []
            self.auto_inc_pk = False
            self.df_original = pd.DataFrame()
            self.model.clear()
            self.load_tables()

            QMessageBox.information(self, "OK", "Using database: {}".format(db))
        except Exception as e:
            QMessageBox.critical(self, "Use DB failed", str(e))

    def load_tables(self):
        self.table_list.clear()

        try:
            with self.engine.connect() as conn:
                rows = conn.execute(text("SHOW TABLES")).fetchall()

            for row in rows:
                self.table_list.addItem(row[0])
        except Exception as e:
            QMessageBox.critical(self, "Load tables failed", str(e))

    def load_table(self):
        if not self.engine or not self.current_db:
            QMessageBox.warning(self, "Warning", "Connect + Use Database first!")
            return

        item = self.table_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Warning", "Please choose a table.")
            return

        table = item.text()
        self.current_table = table

        try:
            insp = inspect(self.engine)

            pk_info = insp.get_pk_constraint(table)
            self.pk_cols = pk_info.get("constrained_columns", []) or []
            self.auto_inc_pk = (len(self.pk_cols) == 1 and self.pk_cols[0].lower() == "id")

            self.df_original = pd.read_sql("SELECT * FROM `{}`".format(table), self.engine)
            self._df_to_model(self.df_original)

            QMessageBox.information(
                self,
                "Loaded",
                "Table: {}\nPrimary key: {}".format(
                    table,
                    ", ".join(self.pk_cols) if self.pk_cols else "(none)"
                )
            )
        except Exception as e:
            QMessageBox.critical(self, "Load table failed", str(e))

    def refresh_table(self):
        if self.current_table:
            self.load_table()

    def _df_to_model(self, df):
        self.model.clear()
        self.model.setColumnCount(len(df.columns))
        self.model.setHorizontalHeaderLabels([str(c) for c in df.columns])

        for r in range(len(df)):
            row_items = []
            for c, col in enumerate(df.columns):
                val = df.iloc[r, c]
                text_val = "" if pd.isna(val) else str(val)

                item = QStandardItem(text_val)

                if col in self.pk_cols and self.auto_inc_pk:
                    item.setEditable(False)
                else:
                    item.setEditable(True)

                row_items.append(item)

            self.model.appendRow(row_items)

        self.table_view.resizeColumnsToContents()

    def _model_to_df(self):
        cols = [self.model.headerData(i, Qt.Horizontal) for i in range(self.model.columnCount())]
        data = []

        for r in range(self.model.rowCount()):
            row = []
            for c in range(self.model.columnCount()):
                item = self.model.item(r, c)
                row.append(item.text() if item else "")
            data.append(row)

        return pd.DataFrame(data, columns=cols)

    def add_row(self):
        if self.model.columnCount() == 0:
            QMessageBox.warning(self, "Warning", "Load a table first.")
            return

        empty_row = []
        for c in range(self.model.columnCount()):
            col = self.model.headerData(c, Qt.Horizontal)
            item = QStandardItem("")

            if col in self.pk_cols and self.auto_inc_pk:
                item.setEditable(False)
            else:
                item.setEditable(True)

            empty_row.append(item)

        self.model.appendRow(empty_row)

    def delete_selected(self):
        selection_model = self.table_view.selectionModel()
        if selection_model is None:
            return

        idxs = selection_model.selectedRows()
        if not idxs:
            return

        for idx in sorted(idxs, key=lambda x: x.row(), reverse=True):
            self.model.removeRow(idx.row())

    def save_changes(self):
        if not self.engine or not self.current_table:
            QMessageBox.warning(self, "Warning", "Load a table first.")
            return

        if not self.pk_cols:
            QMessageBox.critical(
                self,
                "Save blocked",
                "Table này không có PRIMARY KEY.\nĐể update/delete an toàn, hãy thêm PK trước."
            )
            return

        try:
            df_new = self._model_to_df()

            def pk_key_from_row(row):
                return tuple(str(row[pk]).strip() for pk in self.pk_cols)

            orig_map = {}
            for _, row in self.df_original.iterrows():
                orig_map[pk_key_from_row(row)] = row.to_dict()

            new_map = {}
            new_rows_no_pk = []

            for _, row in df_new.iterrows():
                k = pk_key_from_row(row)

                if self.auto_inc_pk and len(self.pk_cols) == 1 and is_blank(k[0]):
                    new_rows_no_pk.append(row.to_dict())
                else:
                    new_map[k] = row.to_dict()

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

                for col in df_new.columns:
                    if col in self.pk_cols:
                        continue

                    ov = "" if old_row.get(col) is None else str(old_row.get(col))
                    nv = "" if new_row.get(col) is None else str(new_row.get(col))

                    if ov != nv:
                        changed = True
                        break

                if changed:
                    update_keys.append(k)

            with self.engine.begin() as conn:
                for k in delete_keys:
                    where_clause = " AND ".join(
                        ["`{}`=:pk_{}".format(pk, i) for i, pk in enumerate(self.pk_cols)]
                    )
                    params = {"pk_{}".format(i): k[i] for i in range(len(self.pk_cols))}
                    sql = "DELETE FROM `{}` WHERE {}".format(self.current_table, where_clause)
                    conn.execute(text(sql), params)

                for k in insert_keys:
                    row = new_map[k]
                    cols = list(df_new.columns)

                    col_clause = ", ".join(["`{}`".format(c) for c in cols])
                    val_clause = ", ".join([":{}".format(c) for c in cols])

                    sql = "INSERT INTO `{}` ({}) VALUES ({})".format(
                        self.current_table, col_clause, val_clause
                    )
                    conn.execute(text(sql), row)

                for row in new_rows_no_pk:
                    cols = [c for c in df_new.columns if c not in self.pk_cols]
                    col_clause = ", ".join(["`{}`".format(c) for c in cols])
                    val_clause = ", ".join([":{}".format(c) for c in cols])
                    params = {c: row.get(c) for c in cols}

                    sql = "INSERT INTO `{}` ({}) VALUES ({})".format(
                        self.current_table, col_clause, val_clause
                    )
                    conn.execute(text(sql), params)

                for k in update_keys:
                    row = new_map[k]
                    set_cols = [c for c in df_new.columns if c not in self.pk_cols]

                    set_clause = ", ".join(["`{}`=:{}".format(c, c) for c in set_cols])
                    where_clause = " AND ".join(
                        ["`{}`=:pk_{}".format(pk, i) for i, pk in enumerate(self.pk_cols)]
                    )

                    params = {c: row.get(c) for c in set_cols}
                    params.update({"pk_{}".format(i): k[i] for i in range(len(self.pk_cols))})

                    sql = "UPDATE `{}` SET {} WHERE {}".format(
                        self.current_table, set_clause, where_clause
                    )
                    conn.execute(text(sql), params)

            QMessageBox.information(
                self,
                "Saved",
                "DELETE: {} | INSERT: {} | UPDATE: {}".format(
                    len(delete_keys),
                    len(insert_keys) + len(new_rows_no_pk),
                    len(update_keys)
                )
            )

            self.refresh_table()

        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MySQLAdminGUI()
    w.show()
    sys.exit(app.exec_())
