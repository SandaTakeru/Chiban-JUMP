# -*- coding: utf-8 -*-


import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QProgressDialog
from qgis.core import QgsVectorLayer
from qgis.PyQt.QtCore import Qt

FORM_CLASS, _ = uic.loadUiType(os.path.join(
	os.path.dirname(__file__), 'chiban_jump_dialog_base.ui'))


class ChibanJumpDialog(QtWidgets.QDialog, FORM_CLASS):
	def __init__(self, parent=None):
		super(ChibanJumpDialog, self).__init__(parent)
		self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)  # 常に最前面に表示
		self.setupUi(self)

		# 探索木データ構造を初期化
		self.data_tree = {}

		# 各選択変更時の処理を設定
		self.chibankukaku.layerChanged.connect(self.initialize_data_tree)
		self.city_selector.currentIndexChanged.connect(self.populate_ooaza_selector)
		self.ooaza_selector.currentIndexChanged.connect(self.populate_chome_selector)
		self.chome_selector.currentIndexChanged.connect(self.populate_koaza_selector)
		self.koaza_selector.currentIndexChanged.connect(self.populate_yobi_selector)
		self.yobi_selector.currentIndexChanged.connect(self.populate_chiban_selector)

		# プラグイン起動時に初期化
		self.initialize_data_tree()
		self.populate_city_selector()

	def initialize_data_tree(self):
		"""探索木データ構造を作成"""
		layer = self.chibankukaku.currentLayer()
		if not layer or not isinstance(layer, QgsVectorLayer):
			self.data_tree = {}
			return

		# フィールド名
		field_names = ["市区町村名", "大字名", "丁目名", "小字名", "予備名", "地番"]
		field_indices = {name: layer.fields().indexFromName(name) for name in field_names if name in [field.name() for field in layer.fields()]}

		# プログレスダイアログを作成
		progress = QProgressDialog("探索木を作成中...", "キャンセル", 0, layer.featureCount(), self)
		progress.setWindowModality(Qt.WindowModal)
		progress.setValue(0)

		# 探索木の構築
		self.data_tree = {}
		for i, feature in enumerate(layer.getFeatures()):
			if progress.wasCanceled():
				self.data_tree = {}
				break

			current_level = self.data_tree
			for field in field_names:
				value = str(feature[field_indices[field]]) if field in field_indices else None
				if value not in current_level:
					current_level[value] = {}
				current_level = current_level[value]

			# プログレスを更新
			progress.setValue(i + 1)

		progress.close()

		# セレクタを順次更新
		self.populate_city_selector()

	def populate_city_selector(self):
		"""市区町村セレクタを更新"""
		self.city_selector.clear()
		if not self.data_tree:
			return
		self.city_selector.addItems(sorted(self.data_tree.keys()))
		if len(self.data_tree) == 1:
			self.city_selector.setCurrentIndex(0)
		self.populate_ooaza_selector()

	def populate_ooaza_selector(self):
		"""大字セレクタを更新"""
		self.ooaza_selector.clear()
		selected_city = self.city_selector.currentText()
		if not selected_city or selected_city not in self.data_tree:
			return
		self.ooaza_selector.addItems(sorted(self.data_tree[selected_city].keys()))
		if len(self.data_tree[selected_city]) == 1:
			self.ooaza_selector.setCurrentIndex(0)
		self.populate_chome_selector()

	def populate_chome_selector(self):
		"""丁目セレクタを更新"""
		self.chome_selector.clear()
		selected_city = self.city_selector.currentText()
		selected_ooaza = self.ooaza_selector.currentText()
		if not selected_city or not selected_ooaza or selected_ooaza not in self.data_tree.get(selected_city, {}):
			return

		# 丁目名を数値としてソート
		def sort_key(value):
			try:
				return int(value.replace("丁目", "").strip())  # "1丁目" → 1
			except ValueError:
				return float("inf")  # 数値に変換できない場合は最後に配置

		chome_values = self.data_tree[selected_city][selected_ooaza].keys()
		sorted_chome_values = sorted(chome_values, key=sort_key)
		self.chome_selector.addItems(sorted_chome_values)

		if len(sorted_chome_values) == 1:
			self.chome_selector.setCurrentIndex(0)
		self.populate_koaza_selector()

	def populate_koaza_selector(self):
		"""小字セレクタを更新"""
		self.koaza_selector.clear()
		selected_city = self.city_selector.currentText()
		selected_ooaza = self.ooaza_selector.currentText()
		selected_chome = self.chome_selector.currentText()
		if not selected_city or not selected_ooaza or not selected_chome or selected_chome not in self.data_tree.get(selected_city, {}).get(selected_ooaza, {}):
			return
		self.koaza_selector.addItems(sorted(self.data_tree[selected_city][selected_ooaza][selected_chome].keys()))
		if len(self.data_tree[selected_city][selected_ooaza][selected_chome]) == 1:
			self.koaza_selector.setCurrentIndex(0)
		self.populate_yobi_selector()

	def populate_yobi_selector(self):
		"""予備セレクタを更新"""
		self.yobi_selector.clear()
		selected_city = self.city_selector.currentText()
		selected_ooaza = self.ooaza_selector.currentText()
		selected_chome = self.chome_selector.currentText()
		selected_koaza = self.koaza_selector.currentText()
		if not selected_city or not selected_ooaza or not selected_chome or not selected_koaza or selected_koaza not in self.data_tree.get(selected_city, {}).get(selected_ooaza, {}).get(selected_chome, {}):
			return
		self.yobi_selector.addItems(sorted(self.data_tree[selected_city][selected_ooaza][selected_chome][selected_koaza].keys()))
		if len(self.data_tree[selected_city][selected_ooaza][selected_chome][selected_koaza]) == 1:
			self.yobi_selector.setCurrentIndex(0)
		self.populate_chiban_selector()

	def populate_chiban_selector(self):
		"""地番セレクタを更新"""
		self.chiban_selector.clear()

		# 上位の選択値を取得
		selected_city = self.city_selector.currentText()
		selected_ooaza = self.ooaza_selector.currentText()
		selected_chome = self.chome_selector.currentText()
		selected_koaza = self.koaza_selector.currentText()
		selected_yobi = self.yobi_selector.currentText()

		# 地番の候補を収集
		def collect_chiban_values(tree, keys):
			if not keys:
				return tree.keys()
			key = keys[0]
			if key in tree:
				return collect_chiban_values(tree[key], keys[1:])
			return []

		chiban_values = collect_chiban_values(
			self.data_tree,
			[selected_city, selected_ooaza, selected_chome, selected_koaza, selected_yobi]
		)

		# 地番を数列としてソート
		def sort_chiban(value):
			# ハイフンで分割し、各部分を数値として扱う
			parts = value.split('-')
			return [int(part) if part.isdigit() else float('inf') for part in parts]

		sorted_chiban_values = sorted(chiban_values, key=sort_chiban)

		# 地番セレクタを更新
		self.chiban_selector.addItems(sorted_chiban_values)
		if len(sorted_chiban_values) == 1:
			self.chiban_selector.setCurrentIndex(0)