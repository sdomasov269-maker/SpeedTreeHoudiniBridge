"""Localized plugin controls; native renderer diagnostics retain their original language."""
LANGUAGES = (("en", "English"), ("ru", "Русский"), ("ja", "日本語"), ("zh", "简体中文"), ("zh_TW", "繁體中文"))
KEYS = ("browse", "scale", "roughness", "normal", "flip", "scene", "camera", "dome", "sun", "view", "quarter", "front", "side", "import", "details", "ready", "busy", "done", "error", "materials", "polygons", "light", "unavailable")
ROWS = {
"en": ("Browse…", "Scale", "Roughness", "Normal strength", "Flip normal Y", "Scene", "Camera", "Soft light", "Sun", "Camera view", "Three-quarter", "Front", "Side", "Import tree", "Details", "Select a .stmat file", "Importing…", "Import complete", "Import failed", "Materials", "Polygons", "Light", "Renderer is not loaded"),
"ru": ("Выбрать…", "Масштаб", "Шероховатость", "Сила нормалей", "Инвертировать Y нормалей", "Сцена", "Камера", "Мягкий свет", "Солнце", "Ракурс камеры", "Три четверти", "Спереди", "Сбоку", "Импортировать дерево", "Подробности", "Выберите файл .stmat", "Импорт…", "Импорт завершён", "Ошибка импорта", "Материалы", "Полигоны", "Свет", "Рендер-плагин не загружен"),
"ja": ("参照…", "スケール", "ラフネス", "法線の強度", "法線の Y を反転", "シーン", "カメラ", "ソフトライト", "太陽", "カメラの角度", "斜め", "正面", "側面", "ツリーを読み込む", "詳細", ".stmat ファイルを選択", "読み込み中…", "読み込み完了", "読み込みエラー", "マテリアル", "ポリゴン", "ライト", "レンダラーがありません"),
"zh": ("浏览…", "缩放", "粗糙度", "法线强度", "翻转法线 Y", "场景", "相机", "柔光", "太阳", "相机视角", "斜视", "正面", "侧面", "导入树木", "详情", "选择 .stmat 文件", "正在导入…", "导入完成", "导入失败", "材质", "多边形", "灯光", "未加载渲染器"),
"zh_TW": ("瀏覽…", "縮放", "粗糙度", "法線強度", "翻轉法線 Y", "場景", "相機", "柔光", "太陽", "相機視角", "斜視", "正面", "側面", "匯入樹木", "詳細資訊", "選擇 .stmat 檔案", "正在匯入…", "匯入完成", "匯入失敗", "材質", "多邊形", "燈光", "未載入算圖引擎"),
}
TRANSLATIONS = {code: dict(zip(KEYS, row)) for code, row in ROWS.items()}
def translate(code, key):
    return TRANSLATIONS.get(code, TRANSLATIONS["en"])[key]
