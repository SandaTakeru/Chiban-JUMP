from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import (
	QgsExpression,
	QgsFeatureRequest,
	QgsGeometry,
	QgsMapLayerProxyModel,
	Qgis
)

from .resources import *
from .chiban_jump_dialog import ChibanJumpDialog
import os.path


class ChibanJump:
	def __init__(self, iface):
		self.iface = iface
		self.plugin_dir = os.path.dirname(__file__)
		locale = QSettings().value('locale/userLocale')[0:2]
		locale_path = os.path.join(
			self.plugin_dir,
			'i18n',
			'ChibanJump_{}.qm'.format(locale))

		if os.path.exists(locale_path):
			self.translator = QTranslator()
			self.translator.load(locale_path)
			QCoreApplication.installTranslator(self.translator)

		self.actions = []
		self.menu = self.tr(u'&地番JUMP')
		self.first_start = None

	def tr(self, message):
		return QCoreApplication.translate('ChibanJump', message)

	def add_action(
		self,
		icon_path,
		text,
		callback,
		enabled_flag=True,
		add_to_menu=True,
		add_to_toolbar=True,
		status_tip=None,
		whats_this=None,
		parent=None):
		icon = QIcon(icon_path)
		action = QAction(icon, text, parent)
		action.triggered.connect(callback)
		action.setEnabled(enabled_flag)

		if status_tip is not None:
			action.setStatusTip(status_tip)

		if whats_this is not None:
			action.setWhatsThis(whats_this)

		if add_to_toolbar:
			self.iface.addToolBarIcon(action)

		if add_to_menu:
			self.iface.addPluginToVectorMenu(
				self.menu,
				action)

		self.actions.append(action)

		return action

	def initGui(self):
		icon_path = os.path.join(self.plugin_dir, 'icon.png')  # icon.png を指定
		self.add_action(
			icon_path,
			text=self.tr(u'地番JUMP'),
			callback=self.run,
			parent=self.iface.mainWindow())

		self.first_start = True

	def unload(self):
		for action in self.actions:
			self.iface.removePluginVectorMenu(
				self.tr(u'&地番JUMP'),
				action)
			self.iface.removeToolBarIcon(action)

	def build_conditions(self, fields):
		"""
		フィールドと値の辞書を受け取り、条件式を構築するヘルパー関数。
		"""
		conditions = []
		for field, value in fields.items():
			if value is not None and value.strip():  # 空白でない場合
				if value == "NULL":
					conditions.append(f'"{field}" IS NULL')
				else:
					conditions.append(f'"{field}" = \'{value}\'')
			# 空白の場合は条件を追加しない（無条件）
		return conditions

	def run(self):
		if self.first_start == True:
			self.first_start = False
			self.dlg = ChibanJumpDialog()

			# chibankukaku にポリゴンレイヤのフィルタを設定
			self.dlg.chibankukaku.setFilters(QgsMapLayerProxyModel.PolygonLayer)

		self.dlg.show()
		result = self.dlg.exec_()
		if result:
			# 選択したレイヤを取得
			selected_layer = self.dlg.chibankukaku.currentLayer()

			# 各フィールドの値を取得
			city = self.dlg.city_selector.currentText()
			ooaza = self.dlg.ooaza_selector.currentText()
			chome = self.dlg.chome_selector.currentText()
			koaza = self.dlg.koaza_selector.currentText()
			yobi = self.dlg.yobi_selector.currentText()
			chiban = self.dlg.chiban_selector.currentText()

			# デバッグ用の出力
			print(f"選択された値: 市区町村名={city}, 大字名={ooaza}, 丁目名={chome}, 小字名={koaza}, 予備名={yobi}, 地番={chiban}")

			if selected_layer:
				# 各フィールドの値を辞書にまとめる
				fields = {
					"市区町村名": city,
					"大字名": ooaza,
					"丁目名": chome,
					"小字名": koaza,
					"予備名": yobi,
					"地番": chiban
				}

				# 条件式を構築
				conditions = self.build_conditions(fields)

				# 条件式をデバッグ出力
				print(f"構築された条件式: {' AND '.join(conditions)}")

				if conditions:
					expression = QgsExpression(" AND ".join(conditions))
					request = QgsFeatureRequest(expression)
					selected_features = [f for f in selected_layer.getFeatures(request)]

					# 検索結果をデバッグ出力
					print(f"検索結果の地物数: {len(selected_features)}")

					if selected_features:
						# 地物を選択
						selected_layer.selectByIds([f.id() for f in selected_features])

						# 選択した地物にズーム
						extent = QgsGeometry.unaryUnion([f.geometry() for f in selected_features]).boundingBox()
						self.iface.mapCanvas().setExtent(extent)
						self.iface.mapCanvas().refresh()
					else:
						self.iface.messageBar().pushMessage(
							"情報", "該当する地物が見つかりませんでした。条件を確認してください。", level=Qgis.Info)
				else:
					self.iface.messageBar().pushMessage(
						"エラー", "検索条件が入力されていません。すべてのフィールドが空白です。", level=Qgis.Critical)
			else:
				self.iface.messageBar().pushMessage(
					"エラー", "レイヤが選択されていません。ポリゴンレイヤを選択してください。", level=Qgis.Critical)