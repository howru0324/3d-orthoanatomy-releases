import base64, gzip, hashlib, json, re, shutil, urllib.parse, urllib.request, zipfile
from pathlib import Path
cfg=json.loads(Path("publication.json").read_text(encoding="utf-8"))
version="0.4.2-beta.6"
assert cfg["version"]==version
url=urllib.parse.urlsplit(cfg["artifact_url"])
assert url.scheme=="https" and url.hostname.endswith(".oaiusercontent.com") and not url.username
expected=cfg["artifact_sha256"].removeprefix("sha256:")
assert re.fullmatch("[0-9a-f]{64}",expected)
digest=hashlib.sha256(); total=0
with urllib.request.urlopen(cfg["artifact_url"],timeout=90) as response, open("installer.zip","wb") as out:
 while True:
  data=response.read(1024*1024)
  if not data:break
  total+=len(data)
  assert total<800*1024*1024
  digest.update(data);out.write(data)
assert digest.hexdigest()==expected,"Artifact archive hash mismatch"
exe="3D-orthoanatomy-Setup-"+version+".exe"
names={exe,exe+".blockmap","beta.yml"}
root=Path("verified");root.mkdir()
with zipfile.ZipFile("installer.zip") as archive:
 files=[e for e in archive.infolist() if not e.is_dir()]
 assert len(files)==3 and {Path(e.filename).name for e in files}==names,"Only installer assets may be published"
 for entry in files:
  with archive.open(entry) as source, open(root/Path(entry.filename).name,"wb") as target:shutil.copyfileobj(source,target)
manifest=(root/"beta.yml").read_text(encoding="utf-8")
assert re.search(r"^version: "+re.escape(version)+r"\s*$",manifest,re.M)
assert exe in manifest
sha=hashlib.sha512()
with open(root/exe,"rb") as f:
 assert f.read(2)==b"MZ";f.seek(0)
 for part in iter(lambda:f.read(1024*1024),b""):sha.update(part)
assert base64.b64encode(sha.digest()).decode()==re.search(r"^sha512: (\S+)",manifest,re.M)[1]
assert ("size: "+str((root/exe).stat().st_size)) in manifest
blockmap=json.loads(gzip.decompress((root/(exe+".blockmap")).read_bytes()))
assert blockmap["version"]=="2" and blockmap["files"]
assets=[]
for name in sorted(names):
 h=hashlib.sha256()
 with open(root/name,"rb") as f:
  for part in iter(lambda:f.read(1024*1024),b""):h.update(part)
 assets.append({"name":name,"size":(root/name).stat().st_size,"digest":"sha256:"+h.hexdigest()})
Path("verified-assets.json").write_text(json.dumps(assets),encoding="utf-8")
print(json.dumps({"version":version,"archiveVerified":True,"manifestVerified":True,"blockmapVerified":True,"assets":assets}))
