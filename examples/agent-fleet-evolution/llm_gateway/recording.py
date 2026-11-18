"""Private durable recorder; no application/database configuration is imported."""
import os
from pathlib import Path
from .contract import canonical
def atomic(path,value):
 path=Path(path);temp=path.with_name(path.name+".writing")
 with temp.open("wb") as f:f.write(canonical(value)+b"\n");f.flush();os.fsync(f.fileno())
 os.replace(temp,path)
