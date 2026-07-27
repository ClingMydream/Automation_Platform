import json

from app.modules.api_workspace.service import parse_api_import


def test_import_csv_with_custom_columns():
    content="名称,请求方式,请求地址,负责人\n查询用户,GET,https://example.com/users/1,cling\n".encode("utf-8")
    rows=parse_api_import("apis.csv",content)
    assert rows[0]["name"]=="查询用户"
    assert rows[0]["method"]=="GET"
    assert rows[0]["custom_fields"]["负责人"]=="cling"


def test_import_postman_collection_and_nested_folder():
    collection={"info":{"name":"Demo"},"item":[{"name":"用户","item":[{"name":"详情","request":{"method":"GET","url":{"raw":"https://example.com/users/1"},"header":[]}}]}]}
    rows=parse_api_import("demo.postman_collection.json",json.dumps(collection).encode())
    assert rows==[{"name":"用户 / 详情","method":"GET","url":"https://example.com/users/1","description":"","tags":[],"custom_fields":{}}]


def test_import_plain_json_list():
    rows=parse_api_import("apis.json",json.dumps([{"name":"创建订单","method":"post","url":"https://example.com/orders","custom_fields":{"环境":"test"}}]).encode())
    assert rows[0]["method"]=="POST"
    assert rows[0]["custom_fields"]=={"环境":"test"}
