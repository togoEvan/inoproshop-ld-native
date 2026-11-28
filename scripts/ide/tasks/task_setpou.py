# -*- coding: utf-8 -*-
# @ipy2
"""task_setpou.py —— 带乐观锁的 POU 源码写入（学 inoproshop-mcp set_pou_code.py）

为什么需要它：do_replace.py 的改名让位法能防同名冲突，但防不住「别人在这期间改过这个 POU」
—— 两个 agent 同时写同一个工程时，后写的人会把前一个人的改动静默覆盖。
本脚本的做法：哈希对不上就拒写（STALE_WRITE），写完逐字读回，不符就回滚并 save。

输入  <BASE>/ipc/setpou_args.json
  { pou, code?, decl?, expect_hash?, save? (默认 true) }
  expect_hash = sha256((decl + u'\0' + impl).encode('utf-8')).hexdigest()，由调用方先读再算；
  不传则跳过哈希校验（仅用于首次写入）。
输出  <BASE>/ipc/setpou_result.json + setpou.log（末尾 ### RESULT_JSON ### 包裹）
退出  0 成功 / 1 失败（STALE_WRITE、READBACK_MISMATCH、回滚结果都写在 RESULT_JSON 里）
"""
import io
import os
import sys
import traceback
import hashlib

_HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.insert(0, os.path.dirname(_HERE))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
ARGS = os.path.join(IPC, 'setpou_args.json')
RES = os.path.join(IPC, 'setpou_result.json')
LOG = os.path.join(IPC, 'setpou.log')


def _open(path, mode='w'):
    return io.open(path, mode, encoding='utf-8')


def log(msg):
    f = _open(LOG, 'a')
    try:
        f.write(unicode(msg) + u'\n')
        f.flush()
    finally:
        f.close()


def load_args():
    f = _open(ARGS, 'r')
    try:
        raw = f.read()
    finally:
        f.close()
    import json
    return json.loads(raw)


def dump_json(path, obj):
    f = _open(path, 'w')
    try:
        import json
        f.write(json.dumps(obj, ensure_ascii=False, indent=2))
        f.flush()
    finally:
        f.close()


def emit(obj):
    log(u'### RESULT_JSON ###')
    import json
    log(json.dumps(obj, ensure_ascii=False, indent=2))
    log(u'### END_RESULT_JSON ###')
    dump_json(RES, obj)


def norm(s):
    if s is None:
        return u''
    return unicode(s).replace(u'\r\n', u'\n').replace(u'\r', u'\n')


def sig(decl, impl):
    h = hashlib.sha256()
    h.update(norm(decl).encode('utf-8'))
    h.update(u'\x00'.encode('utf-8'))
    h.update(norm(impl).encode('utf-8'))
    return h.hexdigest()


def find_pou(root, name):
    # 广度优先：Application 的直接子对象优先于 Task Configuration 里的调用条目
    level = [root]
    while level:
        nxt = []
        for node in level:
            try:
                kids = node.get_children()
            except Exception:
                kids = None
            if not kids:
                continue
            for o in kids:
                try:
                    if o.get_name() == name:
                        return o
                except Exception:
                    pass
                nxt.append(o)
        level = nxt
    return None


def texts(o):
    if not hasattr(o, 'textual_declaration') or not hasattr(o, 'textual_implementation'):
        raise RuntimeError(u'POU 不是可读源码对象（没有 textual_declaration/textual_implementation）')
    return o.textual_declaration.text, o.textual_implementation.text


def main():
    args = None
    old_decl = old_impl = None
    decl_doc = impl_doc = None
    try:
        args = load_args()
        name = args.get('pou')
        if not name:
            raise RuntimeError(u'missing pou')
        proj = projects.primary
        if proj is None:
            raise RuntimeError(u'没有打开的工程（projects.primary 为 None）')
        app = proj.active_application
        o = find_pou(app, name)
        if o is None:
            raise RuntimeError(u'POU not found: %s' % name)
        old_decl, old_impl = texts(o)
        before = sig(old_decl, old_impl)
        expect = args.get('expect_hash')
        if expect and unicode(expect).lower() != before:
            raise RuntimeError(u'STALE_WRITE: POU changed since read (expect %s got %s)'
                               % (unicode(expect), before))
        new_decl = args.get('decl')
        new_impl = args.get('code')
        if new_decl is None and new_impl is None:
            raise RuntimeError(u'nothing to write: 至少给 code 或 decl 之一')
        decl_doc = o.textual_declaration
        impl_doc = o.textual_implementation
        if new_decl is not None:
            decl_doc.replace(unicode(new_decl))
        if new_impl is not None:
            impl_doc.replace(unicode(new_impl))
        got_decl, got_impl = texts(o)
        bad = []
        if new_decl is not None and norm(got_decl) != norm(new_decl):
            bad.append('decl')
        if new_impl is not None and norm(got_impl) != norm(new_impl):
            bad.append('code')
        if bad:
            raise RuntimeError(u'READBACK_MISMATCH: ' + u','.join(bad))
        after = sig(got_decl, got_impl)
        saved = False
        if args.get('save', True):
            proj.save()
            saved = True
        emit({u'ok': True, u'pou': name, u'hash_before': before, u'hash_after': after,
              u'decl_len': len(norm(got_decl)), u'code_len': len(norm(got_impl)),
              u'saved': saved})
        log(u'OK %s saved=%s' % (name, saved))
        return 0
    except Exception, e:
        msg = unicode(e)
        log(u'FAIL %s' % msg)
        log(traceback.format_exc())
        rolled = None
        if args is not None and old_decl is not None:
            try:
                if decl_doc is not None:
                    decl_doc.replace(unicode(old_decl))
                if impl_doc is not None:
                    impl_doc.replace(unicode(old_impl))
                p2 = projects.primary
                if p2 is not None:
                    p2.save()
                rolled = 'ok'
            except Exception, e2:
                rolled = 'FAIL: %s' % unicode(e2)
        emit({u'ok': False, u'error': msg, u'rolled_back': rolled,
              u'trace': traceback.format_exc()})
        return 1


# 通过 eval_file 执行时 __name__ 是 __eval__，不能用 __main__ 守卫
main()