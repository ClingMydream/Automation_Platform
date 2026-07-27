import csv
import io
import json


def parse_api_import(filename:str,content:bytes):
    name=filename.lower()
    if name.endswith(".csv"):
        text=content.decode("utf-8-sig")
        return [normalize_row(row) for row in csv.DictReader(io.StringIO(text))]
    if not name.endswith(".json"):
        raise ValueError("首版仅支持 JSON、CSV 和 Postman Collection JSON")
    payload=json.loads(content.decode("utf-8-sig"))
    if isinstance(payload,list): return [normalize_row(x) for x in payload]
    if isinstance(payload,dict) and "item" in payload:
        rows=[]
        def walk(items,folder=""):
            for item in items:
                current=f"{folder} / {item.get('name','')}".strip(" /")
                if "item" in item: walk(item["item"],current); continue
                request=item.get("request",{}); url=request.get("url","")
                if isinstance(url,dict): url=url.get("raw","")
                headers=request.get("header",[]) or []
                rows.append(normalize_row({"name":current or "未命名接口","method":request.get("method","GET"),"url":url,
                    "description":item.get("description","") if isinstance(item.get("description",""),str) else "",
                    "custom_fields":{"headers":json.dumps(headers,ensure_ascii=False)} if headers else {}}))
        walk(payload["item"]); return rows
    if isinstance(payload,dict): return [normalize_row(payload)]
    raise ValueError("无法识别导入内容")


def normalize_row(row):
    custom=row.get("custom_fields") or {}
    if isinstance(custom,str):
        try: custom=json.loads(custom)
        except json.JSONDecodeError: custom={"备注字段":custom}
    known={"name","method","url","description","tags","custom_fields"}
    custom={**{str(k):str(v) for k,v in custom.items()},**{str(k):str(v) for k,v in row.items() if k not in known and v not in (None,"")}}
    tags=row.get("tags",[])
    if isinstance(tags,str): tags=[x.strip() for x in tags.split(",") if x.strip()]
    return {"name":str(row.get("name") or row.get("名称") or "未命名接口"),"method":str(row.get("method") or row.get("请求方式") or "GET").upper(),
        "url":str(row.get("url") or row.get("请求地址") or ""),"description":str(row.get("description") or row.get("说明") or ""),"tags":tags,"custom_fields":custom}
