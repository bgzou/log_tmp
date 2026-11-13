from docx import Document

p = r"部署测试\02_现场操作\AS2-W与Go2W-B2W模型与训练配置深度对比_20261112.docx"
d = Document(p)
txt = [x.text for x in d.paragraphs]
for t in d.tables:
    for r in t.rows:
        for c in r.cells:
            txt.append(c.text)
bad = [s for s in txt if "**" in s or s.strip().startswith("|") or "`" in s]
print("leftover markup:", len(bad))
for b in bad[:5]:
    print("  ", b[:80])
print("chars:", sum(len(s) for s in txt))
print("empty cells:", sum(1 for t in d.tables for r in t.rows for c in r.cells if not c.text.strip()))
print("tables:", len(d.tables), "paragraphs:", len(d.paragraphs))
