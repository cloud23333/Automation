#!/usr/bin/env python
from __future__ import annotations
import os, re, argparse, collections, tkinter as tk
from tkinter import filedialog
import pandas as pd
from tqdm import tqdm

MAIN_KEY=re.compile(r"(?:^|[_-])main(?:[_-]|$)",re.I)
SIZE_KEY=re.compile(r"(?:^|[_-])size(?:[_-]|$)",re.I)
OPTION_KEY=re.compile(r"(?:^|[_-])option(?:[_-]|$)",re.I)
QTY_KEY=re.compile(r"(?:^|[_-])qty(?:[_-]|$)",re.I)
NOQTY_KEY=re.compile(r"(?:^|[_-])noqty(?:[_-]|$)",re.I)
SKU_RE=re.compile(r"[A-Z0-9]{4,}")
IMG_EXT={".jpg",".jpeg",".png",".webp"}

def classify(fn):
    base=os.path.splitext(fn)[0]
    role="main" if MAIN_KEY.search(base) else "size" if SIZE_KEY.search(base) else "option" if OPTION_KEY.search(base) else None
    if not role:return None
    tag="qty" if role=="option" and QTY_KEY.search(base) else "noqty" if role=="option" and NOQTY_KEY.search(base) else None
    m=SKU_RE.search(base)
    sku=m.group(0) if m else None
    return role,tag,sku

def scan(root):
    recs=[]
    for fc in tqdm(os.listdir(root)):
        p1=os.path.join(root,fc)
        if not os.path.isdir(p1):continue
        for st in os.listdir(p1):
            p2=os.path.join(p1,st)
            if not os.path.isdir(p2):continue
            for sf in os.listdir(p2):
                p3=os.path.join(p2,sf)
                if not os.path.isdir(p3):continue
                for fn in os.listdir(p3):
                    if os.path.splitext(fn)[1].lower() not in IMG_EXT:continue
                    r=classify(fn)
                    if not r:continue
                    role,tag,sku=r
                    recs.append(dict(folder_code=fc,style_name=st,sku_folder=sf,file_path=os.path.join(p3,fn),img_role=role,option_tag=tag,sku_code=sku))
    return recs

def agg(recs,root):
    g=collections.defaultdict(list)
    [g[(r["folder_code"],r["style_name"],r["sku_folder"])].append(r) for r in recs]
    rows,det=[],[]
    for (fc,st,sf),imgs in g.items():
        c=collections.Counter(i["img_role"] for i in imgs)
        qty=sum(1 for i in imgs if i["img_role"]=="option" and i["option_tag"]=="qty")
        noqty=sum(1 for i in imgs if i["img_role"]=="option" and i["option_tag"]=="noqty")
        bad=[i for i in imgs if i["img_role"]=="option" and not i["sku_code"]]
        few=(c["main"]+c["size"])<5
        bad_opt=(noqty==0) or (qty and noqty and qty!=noqty)
        bad_sku=bool(bad)
        row=dict(大类=fc,风格=st,SKU文件夹=sf,文件夹地址=os.path.join(root,fc,st,sf),主图数=c.get("main",0),尺寸图数=c.get("size",0),选项图数=c.get("option",0),带数量张数=qty,不带数量张数=noqty,坏SKU张数=len(bad),**{"主+尺寸<5":int(few),"选项图有问题":int(bad_opt),"有坏SKU":int(bad_sku)})
        rows.append(row)
        det.extend([{**row,"问题选项图路径":i["file_path"],"记录的SKU":i["sku_code"] or ""} for i in bad])
    return pd.DataFrame(rows),pd.DataFrame(det)

def choose_dir():
    root=tk.Tk();root.withdraw()
    return filedialog.askdirectory(title="请选择根文件夹")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root")
    p.add_argument("--out",default="folder_health_issues.xlsx")
    a=p.parse_args()
    if not a.root:
        a.root=choose_dir()
        if not a.root:return
    a.root=os.path.abspath(a.root)
    recs=scan(a.root)
    df1,df2=agg(recs,a.root)
    bad=df1[(df1["主+尺寸<5"]==1)|(df1["选项图有问题"]==1)|(df1["有坏SKU"]==1)]
    with pd.ExcelWriter(a.out,engine="xlsxwriter") as w:
        bad.to_excel(w,sheet_name="问题汇总",index=False)
        df2.to_excel(w,sheet_name="坏SKU明细",index=False)
    print("Done:",a.out)

if __name__=="__main__":main()
