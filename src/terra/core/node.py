"""Node 基底とレジストリ。ステップ名 "gen.noise" → クラス。入力/出力レイヤー名を宣言する。"""
from __future__ import annotations

import importlib

NODES: dict[str, type] = {}


def node(name):
    def deco(cls):
        cls.name = name
        NODES[name] = cls
        return cls
    return deco


class Node:
    name = ""
    inputs: tuple = ()          # 読むラスタレイヤー
    outputs: tuple = ()         # 書くラスタレイヤー(キャッシュ対象)
    vec_outputs: tuple = ()     # 書くベクタ名
    scatter_outputs: tuple = ()  # 書く散布名
    defaults: dict = {}

    def __init__(self, **params):
        self.params = {**self.defaults, **params}

    def run(self, doc, rng):
        raise NotImplementedError


def get_node(name) -> type:
    if name not in NODES:
        importlib.import_module("terra." + name.split(".")[0])   # 各パッケージの __init__ が全ノードを import
    if name not in NODES:
        raise KeyError(f"unknown step: {name}")
    return NODES[name]
