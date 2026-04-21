// gui/web/static/js/dom.js
export const $ = (id) => document.getElementById(id);

export const dom = {
  // topbar
  tb_time: $("tb_time"),
  tb_people: $("tb_people"),
  tb_weather: $("tb_weather"),

  // home status
  floor: $("floor"),
  overload: $("overload"),
  direction: $("direction"),
  door: $("door"),
  people: $("people"),
  clock: $("clock"),
  weather: $("weather"),

  // home bot
  botShell: $("botShell"),
  botMode: $("botMode"),
  state: $("state"),

  // chat screen
  chatMessages: $("chatMessages"),
  chatInput: $("chatInput"),
  botShellChat: $("botShellChat"),
  botModeChat: $("botModeChat"),
  stateChat: $("stateChat"),

  // sos
  sosTime: $("sosTime"),
  sosStatus: $("sosStatus"),
  sosLocation: $("sosLocation"),

  // maint auth / shell
  maintLogin: $("maint-login"),
  maintDash: $("maint-dashboard"),
  maintUser: $("maintUser"),
  maintPass: $("maintPass"),
  maintLan: $("maintLan"),

  // maint merged status/config
  maintMergedStatusCard: $("maintMergedStatusCard"),
  maintFloor: $("maintFloor"),
  maintDirection: $("maintDirection"),
  maintDoor: $("maintDoor"),
  maintPeople: $("maintPeople"),
  maintTime: $("maintTime"),

  // maint layout
  maintBottomGrid: $("maintBottomGrid"),
  maintLookupCard: $("maintLookupCard"),
  maintDataCard: $("maintDataCard"),

  // data manager tabs
  dataTabMysql: $("dataTabMysql"),
  dataTabMongo: $("dataTabMongo"),
  dataPanelMysql: $("dataPanelMysql"),
  dataPanelMongo: $("dataPanelMongo"),
  maintExpandBtn: $("maintExpandBtn"),

  // mysql manager controls
  mysqlHost: $("mysqlHost"),
  mysqlPort: $("mysqlPort"),
  mysqlUser: $("mysqlUser"),
  mysqlPassword: $("mysqlPassword"),
  mysqlConnectBtn: $("mysqlConnectBtn"),
  mysqlDbSelect: $("mysqlDbSelect"),
  mysqlUseDbBtn: $("mysqlUseDbBtn"),
  mysqlLoadTableBtn: $("mysqlLoadTableBtn"),
  mysqlTableList: $("mysqlTableList"),
  mysqlGrid: $("mysqlGrid"),
  mysqlGridStatus: $("mysqlGridStatus"),
  mysqlAddRowBtn: $("mysqlAddRowBtn"),
  mysqlDeleteBtn: $("mysqlDeleteBtn"),
  mysqlSaveBtn: $("mysqlSaveBtn"),
  mysqlRefreshBtn: $("mysqlRefreshBtn"),

  // maint chat widget
  maintChatToggle: $("maintChatToggle"),
  maintChatPanel: $("maintChatPanel"),
  maintChatClose: $("maintChatClose"),
  maintChatMessages: $("maintChatMessages"),
  maintChatInput: $("maintChatInput"),
  maintChatSend: $("maintChatSend"),
};