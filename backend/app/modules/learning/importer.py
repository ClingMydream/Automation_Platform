import hashlib
import stat
import zipfile
from pathlib import Path, PurePosixPath

import bleach
from markdownify import markdownify
from sqlalchemy import select

from app.models.entities import LearningAttachment, LearningImport, LearningNote, LearningNoteFolder

TEXT={".md",".markdown",".html",".htm",".txt"}
FILES={".png",".jpg",".jpeg",".gif",".webp",".pdf",".doc",".docx",".xls",".xlsx",".ppt",".pptx",".json",".yaml",".yml",".zip"}

def import_zip(db, archive:Path, original_name:str, root:Path, limits:dict):
    report={"success":[],"duplicates":[],"failed":[],"unsupported":[]}; folders={}
    def folder_for(parts):
        parent=None; key=""
        for name in parts:
            key += "/"+name
            if key not in folders:
                obj=LearningNoteFolder(name=name,parent_id=parent); db.add(obj); db.flush(); folders[key]=obj.id
            parent=folders[key]
        return parent
    with zipfile.ZipFile(archive) as zf:
        members=zf.infolist()
        if len(members)>limits["entries"]: raise ValueError("ZIP 条目超过限制")
        if sum(i.file_size for i in members)>limits["expanded"]: raise ValueError("ZIP 解压后超过 1GB")
        for i in members:
            path=PurePosixPath(i.filename.replace("\\","/"))
            if path.is_absolute() or ".." in path.parts: raise ValueError("ZIP 包含路径穿越条目")
            if stat.S_ISLNK(i.external_attr>>16): raise ValueError("ZIP 不允许符号链接")
            if i.file_size>10*1024*1024 and i.file_size/max(i.compress_size,1)>200: raise ValueError("ZIP 疑似压缩炸弹")
        for i in (x for x in members if not x.is_dir()):
            path=PurePosixPath(i.filename.replace("\\","/")); ext=path.suffix.lower()
            if ext==".note": report["unsupported"].append({"path":str(path),"reason":"请先导出为 Markdown/HTML"}); continue
            if ext not in TEXT|FILES: report["unsupported"].append({"path":str(path),"reason":"不支持的格式"}); continue
            try:
                raw=zf.read(i)
                if len(raw)>limits["attachment"]: raise ValueError("单文件超过 20MB")
                digest=hashlib.sha256(str(path).encode()+b"\0"+raw).hexdigest()
                if db.scalar(select(LearningNote.id).where(LearningNote.import_fingerprint==digest)):
                    report["duplicates"].append(str(path)); continue
                folder=folder_for(path.parts[:-1])
                if ext in TEXT:
                    try: content=raw.decode("utf-8-sig")
                    except UnicodeDecodeError: content=raw.decode("gb18030",errors="replace")
                    if ext in {".html",".htm"}:
                        tags=set(bleach.sanitizer.ALLOWED_TAGS)|{"p","h1","h2","h3","pre","code","table","thead","tbody","tr","th","td","img"}
                        content=markdownify(bleach.clean(content,tags=tags,attributes={"a":["href"],"img":["src","alt"]},strip=True),heading_style="ATX")
                    elif ext==".txt": content=f"```text\n{content}\n```"
                    note=LearningNote(folder_id=folder,title=path.stem,content_markdown=content,import_fingerprint=digest,import_source_path=str(path)); db.add(note); db.flush()
                else:
                    note=LearningNote(folder_id=folder,title=path.stem,content_markdown=f"# {path.stem}\n\n导入附件：{path.name}",import_fingerprint=digest,import_source_path=str(path)); db.add(note); db.flush()
                    stored=digest+ext; target=root/"attachments"/stored; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
                    db.add(LearningAttachment(note_id=note.id,original_name=path.name,stored_name=stored,content_type="application/octet-stream",size_bytes=len(raw),is_image=ext in {".png",".jpg",".jpeg",".gif",".webp"}))
                report["success"].append(str(path))
            except Exception as exc: report["failed"].append({"path":str(path),"reason":str(exc)})
    record=LearningImport(original_name=original_name,status="partial" if report["failed"] else "completed",report=report); db.add(record); db.commit(); db.refresh(record); report["import_id"]=record.id
    return report
