import assert from "node:assert/strict";
import {
  searchModules,
  readRecentModules,
  MODULE_META,
} from "./workspaceCatalog.js";
const items = [
  { key: "home", label: "工作台" },
  { key: "work_journal", label: "工作手记", sectionLabel: "个人成长" },
  { key: "json_tools", label: "JSON 工具", sectionLabel: "效率工具" },
];
assert.deepEqual(
  searchModules(items, "周报").map((x) => x.key),
  ["work_journal"],
);
assert.deepEqual(
  searchModules(items, "JSON 效率").map((x) => x.key),
  ["json_tools"],
);
assert.deepEqual(
  searchModules(items, "  ").map((x) => x.key),
  items.map((x) => x.key),
);
assert.equal(searchModules(items, "用户管理").length, 0);
assert.equal(searchModules(items, "不存在的功能").length, 0);
assert.equal(Object.keys(MODULE_META).length, 23);
let raw = "invalid";
const storage = {
  getItem: (key) => {
    assert.match(key, /cling:workspace:alice:recent:v1/);
    return raw;
  },
};
assert.deepEqual(
  readRecentModules(storage, "alice", ["home", "json_tools"]),
  [],
);
raw = JSON.stringify([
  { key: "users", at: 1 },
  { key: "home", at: 1 },
  { key: "json_tools", at: 2 },
  { key: "json_tools", at: 3 },
  { key: "work_journal", at: "bad" },
  { key: "work_journal", at: 1e30 },
]);
assert.deepEqual(
  readRecentModules(storage, "alice", ["home", "json_tools", "work_journal"]),
  [{ key: "json_tools", at: 2 }],
);
assert.deepEqual(
  readRecentModules(
    {
      getItem() {
        throw new Error("blocked");
      },
    },
    "alice",
    [],
  ),
  [],
);
assert.deepEqual(
  readRecentModules(
    {
      getItem() {
        return "{}";
      },
    },
    "alice",
    [],
  ),
  [],
);
console.log(
  "PASS workspace search, permission-filtered catalog, account-scoped recent history and damaged/blocked storage.",
);
