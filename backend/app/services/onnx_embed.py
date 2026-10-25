"""Tiny multilingual sentence embedder on onnxruntime + tokenizers (no torch).

Works with the sentence-transformers export of multilingual-e5-base that the team downloaded
(`<dir>/onnx/model*.onnx` + `<dir>/tokenizer.json`). Mean pooling + L2 norm, "query: " prefix for e5 models.
Optional dependency: `pip install onnxruntime tokenizers numpy`. Everything that uses it degrades gracefully when missing.
"""
from __future__ import annotations

import os
from pathlib import Path

PREFERRED = ("model_qint8_avx512_vnni.onnx", "model_O4.onnx", "model.onnx")


class OnnxEmbedder:
    def __init__(self, model_dir: str, onnx_file: str | None = None, max_len: int = 64, threads: int | None = None):
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        d = Path(model_dir)
        self.np = np
        self.tok = Tokenizer.from_file(str(d / "tokenizer.json"))
        self.tok.enable_truncation(max_length=max_len)
        self.tok.enable_padding(pad_id=self.tok.token_to_id("<pad>") or 1, pad_token="<pad>")
        self.prefix = "query: " if "e5" in d.name.lower() else ""
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads or max(1, (os.cpu_count() or 2) - 1)
        files = [onnx_file] if onnx_file else [f for f in PREFERRED if (d / "onnx" / f).exists()]
        last = None
        for f in files:
            try:
                self.sess = ort.InferenceSession(str(d / "onnx" / f), so, providers=["CPUExecutionProvider"])
                self.file = f
                break
            except Exception as exc:  # e.g. an int8 build that this CPU cannot run
                last = exc
        else:
            raise RuntimeError(f"no usable ONNX file in {d / 'onnx'}: {last}")
        self.inputs = {i.name for i in self.sess.get_inputs()}

    def encode(self, texts: list[str], batch: int = 32):
        np = self.np
        out = []
        for i in range(0, len(texts), batch):
            enc = self.tok.encode_batch([self.prefix + t for t in texts[i:i + batch]])
            ids = np.array([e.ids for e in enc], dtype=np.int64)
            mask = np.array([e.attention_mask for e in enc], dtype=np.int64)
            feed = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self.inputs:
                feed["token_type_ids"] = np.zeros_like(ids)
            hid = self.sess.run(None, feed)[0]
            m = mask[..., None].astype(hid.dtype)
            v = (hid * m).sum(1) / np.clip(m.sum(1), 1e-9, None)
            v /= np.clip(np.linalg.norm(v, axis=1, keepdims=True), 1e-9, None)
            out.append(v.astype(np.float32))
        return np.vstack(out) if out else np.zeros((0, 768), dtype=np.float32)

    __call__ = encode
