"""「図で覚える」コーナーの図と問題データを作る。
- 図は Wikimedia Commons の自由ライセンス図（教科書の図）を使い、図の作者が付けた英語ラベルを白で消して番号に置き換える。
  → 正答は「図の作者が付けたラベル」そのもの。日本語名は過去問の公式表記に合わせ、出典で照合済み。
- 問題の元データ: private/figs/fig_questions.json（evidence＝出典の原文の抜き出し。tools/check_evidence.py で照合）
使い方: tools/.venv/bin/python tools/build_figs.py
出力: app/data/figs/<図id>.webp と app/data/figs.json（evidence は除く）
"""
import json
import re
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "private" / "figs"
OUT = ROOT / "app" / "data" / "figs"
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
JFONT = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
PINK = (226, 69, 127)

# rect = 元画像での英語ラベルの位置（x0, y0, x1, y1）。en = 図の原ラベル、ja = 日本語名
FIGS = {
    "brain": {
        "file": "Anatomy_and_physiology_of_animals_Longitudinal_section_through_brain_of_a_dog.jpg",
        "name": "犬の脳（正中断面）", "crop": (0, 228, 623, 563),
        "labels": [
            ("cerebral cortex", "大脳皮質", (0, 307, 86, 321)),
            ("cerebrum", "大脳", (271, 327, 355, 345)),
            ("nerve fibres joining right and left cerebral hemispheres", "脳梁（左右の大脳半球をつなぐ神経線維）", (488, 316, 614, 362)),
            ("3rd ventricle", "第三脳室", (532, 387, 609, 401)),
            ("cerebellum", "小脳", (18, 407, 88, 421)),
            ("spinal cord", "脊髄", (18, 467, 87, 484)),
            ("thalamus", "視床", (375, 478, 441, 495)),
            ("hypothalamus", "視床下部", (375, 510, 462, 527)),
            ("pons", "橋", (249, 522, 286, 536)),
            ("medulla oblongata", "延髄", (146, 540, 257, 557)),
            ("pituitary gland", "下垂体", (275, 540, 362, 557)),
        ],
    },
    "eye": {
        "file": "Anatomy_and_physiology_of_animals_Structure_of_the_eye.jpg", "name": "眼球の構造（模式図）",
        "labels": [
            ("conjunctiva", "結膜", (211, 2, 283, 18)),
            ("retina", "網膜", (412, 2, 453, 15)),
            ("choroid", "脈絡膜", (464, 1, 514, 15)),
            ("cornea", "角膜", (102, 43, 151, 56)),
            ("sclera", "強膜", (585, 96, 627, 110)),
            ("iris", "虹彩", (126, 99, 151, 110)),
            ("fovea", "中心窩", (584, 149, 624, 163)),
            ("pupil", "瞳孔", (116, 163, 151, 180)),
            ("lens", "水晶体", (119, 222, 151, 236)),
            ("optic nerve", "視神経", (586, 240, 656, 256)),
            ("anterior chamber", "前眼房", (47, 280, 157, 294)),
            ("blind spot", "盲点", (399, 345, 462, 362)),
            ("suspensory ligament", "毛様小帯（チン小帯）", (293, 349, 368, 378)),
        ],
    },
    "ear": {
        "file": "Anatomy_and_physiology_of_animals_The_ear.jpg", "name": "耳の構造（模式図）",
        "labels": [
            ("vestibular organ (semicircular canals and otolith organs)", "前庭器官（半規管と耳石器）", (418, 8, 540, 57)),
            ("ear ossicles tiny bones", "耳小骨", (322, 25, 400, 54)),
            ("ear drum", "鼓膜", (254, 48, 313, 62)),
            ("ear pinna", "耳介", (16, 49, 78, 63)),
            ("cochlea", "蝸牛", (530, 85, 582, 99)),
            ("auditory nerve", "聴神経", (507, 255, 596, 270)),
            ("Eustachian tube", "耳管", (278, 261, 376, 275), "R"),
            ("ear canal", "外耳道", (161, 276, 222, 290)),
        ],
        # 区分の英語キャプションは日本語に置き換える（番号は付けない）
        "captions": [("外耳", (216, 333, 276, 346)), ("中耳", (347, 321, 415, 340)), ("内耳", (467, 329, 526, 340))],
    },
    "kidney": {
        "file": "Anatomy_and_physiology_of_animals_Dissected_kidney.jpg", "name": "腎臓の断面（模式図）",
        "labels": [
            ("renal pelvis", "腎盂", (20, 7, 104, 25)),
            ("cortex", "皮質", (507, 35, 556, 49)),
            ("medulla", "髄質", (507, 83, 568, 98)),
            ("renal artery", "腎動脈", (20, 136, 104, 153)),
            ("pyramids", "腎錐体", (507, 151, 576, 169)),
            ("renal vein", "腎静脈", (31, 173, 104, 188)),
            ("fibrous capsule", "線維被膜", (507, 240, 617, 258)),
            ("ureter", "尿管", (56, 299, 105, 313)),
        ],
    },
    "liver": {
        "file": "Anatomy_and_physiology_of_animals_Liver,_gall_bladder_&_pancreas.jpg", "name": "肝臓・胆嚢・膵臓（模式図）",
        "labels": [
            ("diaphragm", "横隔膜", (509, 19, 588, 38)),
            ("bile ducts transporting bile to gall bladder", "胆管（胆汁を胆嚢へ運ぶ）", (509, 71, 643, 105)),
            ("liver", "肝臓", (95, 80, 129, 96)),
            ("gall bladder (under lobe of liver)", "胆嚢", (7, 130, 130, 164)),
            ("pancreas", "膵臓", (511, 160, 573, 176)),
            ("bile duct", "胆管", (450, 208, 508, 224)),
            ("small intestine (duodenum)", "小腸（十二指腸）", (37, 231, 127, 264)),
        ],
    },
    "heart": {
        "file": "Anatomy_and_physiology_of_animals_heart_showing_Coronary_vessels.jpg", "name": "心臓の外観（模式図）",
        "labels": [
            ("aorta", "大動脈", (126, 37, 165, 52)),
            ("pulmonary artery", "肺動脈", (393, 47, 498, 66)),
            ("cranial vena cava", "前大静脈", (58, 69, 167, 85)),
            ("coronary artery and vein", "冠状動脈・冠状静脈", (391, 126, 537, 145)),
            ("coronary artery and vein ", "冠状動脈・冠状静脈", (21, 149, 166, 168)),
            ("caudal vena cava", "後大静脈", (58, 237, 167, 253)),
        ],
    },
    "organs": {
        "file": "Anatomy_and_physiology_of_animals_main_organs_vertebrate_body.jpg", "name": "からだの主な臓器（腹側から見た模式図）",
        "labels": [
            ("thymus", "胸腺", (352, 105, 404, 122)),
            ("left lung", "左肺", (412, 155, 466, 174)),
            ("heart", "心臓", (436, 187, 476, 203)),
            ("diaphragm", "横隔膜", (2, 219, 73, 238)),
            ("stomach", "胃", (390, 233, 448, 249)),
            ("liver", "肝臓", (17, 249, 51, 265)),
            ("spleen", "脾臓", (372, 258, 420, 277)),
            ("small intestine", "小腸", (348, 281, 438, 297)),
            ("right kidney", "右の腎臓", (38, 283, 113, 302)),
            ("ovary", "卵巣", (391, 317, 433, 331)),
            ("bladder", "膀胱", (45, 343, 98, 359)),
            ("uterus", "子宮", (286, 397, 332, 412)),
            ("testis", "精巣", (230, 434, 271, 449)),
        ],
    },
    # ---- 第2弾（SVG は Chrome で描画。rect は等倍での位置） ----
    "heart2": {
        "file": "Heart_diagram-en.svg", "chrome": (893, 703), "name": "心臓の断面（ヒトの図・正面から見たところ）",
        "labels": [
            ("Brachiocephalic artery", "腕頭動脈", (29, 106, 262, 128)),
            ("Superior vena cava", "上大静脈（動物では前大静脈）", (60, 159, 262, 182)),
            ("Right pulmonary arteries", "右肺動脈", (8, 202, 262, 225)),
            ("Right pulmonary veins", "右肺静脈", (29, 267, 262, 290)),
            ("Right atrium", "右心房", (134, 350, 264, 373)),
            ("Atrioventricular (tricuspid) valve", "三尖弁（右房室弁）", (96, 425, 264, 471)),
            ("Chordae tendineae", "腱索", (62, 497, 264, 520)),
            ("Right ventricle", "右心室", (112, 533, 264, 556)),
            ("Inferior vena cava", "下大静脈（動物では後大静脈）", (76, 585, 264, 608)),
            ("Left common carotid artery", "左総頸動脈", (706, 9, 850, 54)),
            ("Left subclavian artery", "左鎖骨下動脈", (706, 74, 870, 119)),
            ("Aorta", "大動脈", (706, 138, 772, 160)),
            ("Left pulmonary arteries", "左肺動脈", (706, 182, 865, 227)),
            ("Left pulmonary veins", "左肺静脈", (706, 249, 865, 295)),
            ("Left atrium", "左心房", (706, 306, 823, 329)),
            ("Semilunar valves", "半月弁", (706, 345, 890, 368)),
            ("Atrioventricular (mitral) valve", "僧帽弁（左房室弁）", (706, 386, 871, 432)),
            ("Left ventricle", "左心室", (706, 447, 847, 470)),
            ("Septum", "心室中隔", (706, 504, 795, 526)),
        ],
    },
    "conduction": {
        # 引き出し線つきの図（等倍＝幅1000pxに縮小した _cs.png での位置）
        "file": "Conductionsystemoftheheart.png", "img": "_cs.png", "name": "心臓の刺激伝導系（ヒトの図）", "r": 15,
        "labels": [
            ("Sinoatrial node", "洞房結節", (0, 284, 207, 321)),
            ("Atrioventricular node", "房室結節", (0, 389, 207, 461)),
            ("Left posterior bundle", "左脚後枝", (20, 496, 207, 576)),
            ("Right bundle", "右脚", (36, 609, 212, 649)),
            ("Bachmann's bundle", "バッハマン束", (781, 242, 957, 326)),
            ("His bundle", "ヒス束", (853, 397, 1000, 436)),
            ("Purkinje fibres", "プルキンエ線維", (850, 579, 975, 661)),
        ],
    },
    "eye2": {
        "file": "Schematic_diagram_of_the_human_eye_en.svg", "chrome": (416, 423), "name": "眼球の水平断面（ヒトの図）",
        "labels": [
            ("Anterior chamber (aqueous humour) Posterior chamber", "前眼房（眼房水）と後眼房", (14, 16, 131, 60)),
            ("Cornea", "角膜", (153, 13, 209, 29)),
            ("Pupil", "瞳孔", (237, 31, 277, 49)),
            ("Uvea", "ぶどう膜", (318, 31, 361, 48)),
            ("Iris", "虹彩", (330, 55, 358, 71)),
            ("Ciliary body", "毛様体", (338, 72, 381, 103)),
            ("Choroid", "脈絡膜", (340, 107, 394, 124)),
            ("Suspensory ligament of lens", "毛様小帯（チン小帯）", (12, 69, 94, 112)),
            ("Lens", "水晶体", (191, 104, 225, 122)),
            ("Sclera", "強膜", (14, 124, 63, 140)),
            ("Vitreous humour", "硝子体", (151, 146, 204, 177)),
            ("Hyaloid canal", "硝子体管", (219, 163, 266, 188)),
            ("Retinal blood vessels", "網膜の血管", (29, 303, 84, 347)),
            ("Retina", "網膜", (336, 312, 380, 330)),
            ("Macula", "黄斑", (326, 336, 373, 354)),
            ("Fovea", "中心窩", (318, 356, 364, 372)),
            ("Optic nerve", "視神経", (149, 383, 223, 401), "L"),
            ("Optic disc", "視神経乳頭（視神経円板）", (296, 383, 364, 401)),
        ],
    },
    "nephron": {
        "file": "Kidney_Nephron.svg", "chrome": (453, 720), "name": "ネフロンと集合管（模式図）", "strip_text": True,
        "labels": [
            ("Proximal convoluted tubule", "近位尿細管", (1, 104, 99, 160)),
            ("Bowman's capsule", "ボーマン嚢", (102, 89, 193, 128)),
            ("Descending Limb of Loop of Henle", "ヘンレのワナの下行脚", (6, 356, 109, 432)),
            ("Distal convoluted tubule", "遠位尿細管", (275, 390, 375, 448)),
            ("Collecting duct", "集合管", (319, 456, 450, 479)),
            ("Loop of Henle", "ヘンレのワナ", (8, 526, 131, 549)),
            ("Ascending Limb of Loop of Henle", "ヘンレのワナの上行脚", (275, 501, 393, 558)),
        ],
    },
    "cell": {
        "file": "Animal_cell_structure_en.svg", "chrome": (512, 342), "name": "動物細胞の構造（模式図）", "r": 6, "band": 4,
        "labels": [
            ("Nuclear pore", "核膜孔", (153, 15, 210, 27)),
            ("Chromatin", "クロマチン", (166, 26, 210, 37)),
            ("Nuclear envelope", "核膜", (135, 37, 210, 48)),
            ("Nucleus", "核", (171, 48, 206, 58)),
            ("Nucleolus", "核小体", (162, 59, 206, 69)),
            ("Plasma membrane", "細胞膜", (47, 125, 126, 136)),
            ("Golgi vesicles (golgi apparatus)", "ゴルジ小胞（ゴルジ体）", (54, 139, 124, 161)),
            ("Ribosomes", "リボソーム", (74, 167, 124, 179)),
            ("Rough endoplasmic reticulum", "粗面小胞体", (9, 181, 126, 193)),
            ("Smooth endoplasmic reticulum", "滑面小胞体", (9, 195, 126, 207)),
            ("Actin Filaments", "アクチンフィラメント", (59, 209, 126, 221)),
            ("Peroxisome", "ペルオキシソーム", (416, 59, 469, 69)),
            ("Microtubule", "微小管", (416, 73, 468, 83)),
            ("Lysosome", "リソソーム", (416, 87, 463, 99)),
            ("Free Ribosomes", "遊離リボソーム", (416, 101, 482, 111)),
            ("Mitochondrion", "ミトコンドリア", (416, 115, 477, 125)),
            ("Intermediate Filaments", "中間径フィラメント", (416, 129, 504, 139)),
            ("Cytoplasm", "細胞質", (416, 239, 465, 250)),
            ("Secretory vesicle", "分泌小胞", (416, 253, 489, 264)),
            ("Centrosome (with 2 centrioles)", "中心体（2個の中心小体）", (415, 266, 491, 288)),
            ("Flagellum", "鞭毛", (206, 301, 251, 313)),
        ],
        "captions": [("核", (133, 5, 173, 16))],
    },
    "gi": {
        "file": "Layers_of_the_GI_Tract_english.svg", "chrome": (700, 431), "name": "消化管の壁の構造（模式図）", "r": 7.5,
        "labels": [
            ("Vein", "静脈", (397, 69, 437, 86)),
            ("Submucosal plexus (Meissner's plexus)", "粘膜下神経叢（マイスナー神経叢）", (252, 84, 395, 120)),
            ("Glands in submucosa", "粘膜下組織の腺", (157, 163, 315, 180)),
            ("Submucosa", "粘膜下組織", (46, 192, 138, 209)),
            ("Gland in mucossa", "粘膜内の腺", (0, 227, 160, 244)),
            ("Duct of gland outside tract", "消化管の外にある腺の導管", (0, 257, 106, 292)),
            ("Lymphatic tissue", "リンパ組織", (0, 302, 127, 319)),
            ("Lumen", "管腔", (0, 319, 50, 336)),
            ("Epithelium (mucosa)", "上皮（粘膜）", (56, 361, 137, 377)),
            ("Lamina propria", "粘膜固有層", (24, 376, 137, 391)),
            ("Muscularis mucosae", "粘膜筋板", (0, 390, 138, 405)),
            ("Mesentery", "腸間膜", (604, 220, 686, 239)),
            ("Artery", "動脈", (604, 240, 657, 258)),
            ("Nerve", "神経", (604, 258, 653, 275)),
            ("Myenteric plexus (Auerbach's plexus)", "筋層間神経叢（アウエルバッハ神経叢）", (536, 279, 680, 311)),
            ("Areolar connective tissue", "疎性結合組織（漿膜）", (535, 332, 700, 347)),
            ("Epithelium (serosa)", "上皮（漿膜）", (535, 347, 614, 363)),
            ("Circular muscle", "輪走筋", (444, 395, 560, 410)),
            ("Longitudinal muscle", "縦走筋", (444, 410, 590, 427)),
        ],
        "captions": [("粘膜", (71, 345, 140, 361)), ("漿膜", (535, 316, 597, 332)), ("筋層", (444, 379, 534, 395))],
    },
    "bacteria": {
        "file": "Average_prokaryote_cell-_en.svg", "chrome": (650, 390), "name": "細菌（原核細胞）の構造（模式図）",
        "labels": [
            ("Capsule", "莢膜", (221, 14, 288, 33)),
            ("Cell wall", "細胞壁", (221, 33, 288, 50)),
            ("Plasma membrane", "細胞膜", (151, 49, 288, 66)),
            ("Cytoplasm", "細胞質", (143, 77, 226, 98)),
            ("Ribosomes", "リボソーム", (88, 111, 174, 129)),
            ("Plasmid", "プラスミド", (95, 128, 159, 146)),
            ("Pili", "線毛", (92, 149, 124, 168)),
            ("Flagellum", "鞭毛", (424, 305, 501, 326)),
            ("Nucleoid (circular DNA)", "核様体（環状DNA）", (424, 327, 531, 363)),
        ],
    },
    "neuron": {
        "file": "Complete_neuron_cell_diagram_en.svg", "chrome": (819, 596), "name": "ニューロンの構造（模式図）", "r": 9,
        "labels": [
            ("Dendrites", "樹状突起", (106, 37, 187, 57)),
            ("Microtubule", "微小管", (265, 37, 355, 55)),
            ("Neurofibrils", "神経原線維", (265, 57, 353, 74)),
            ("Neurotransmitter", "神経伝達物質", (235, 78, 364, 95)),
            ("Receptor", "受容体", (280, 104, 349, 124)),
            ("Synapse", "シナプス", (416, 32, 481, 52)),
            ("Synaptic vesicles", "シナプス小胞", (562, 62, 684, 83)),
            ("Synapse (Axoaxonic)", "シナプス（軸索－軸索間）", (562, 85, 696, 106)),
            ("Synaptic cleft", "シナプス間隙", (563, 109, 663, 130)),
            ("Axonal terminal", "軸索終末", (562, 132, 678, 151)),
            ("Rough ER (Nissl body)", "粗面小胞体（ニッスル小体）", (97, 139, 177, 167)),
            ("Polyribosomes", "ポリリボソーム", (42, 176, 150, 197)),
            ("Ribosomes", "リボソーム", (53, 206, 135, 224)),
            ("Golgi apparatus", "ゴルジ装置（ゴルジ体）", (4, 233, 119, 254)),
            ("Synapse (Axosomatic)", "シナプス（軸索－細胞体間）", (328, 210, 399, 241)),
            ("Node of Ranvier", "ランビエ絞輪", (563, 182, 675, 201), "R"),
            ("Myelin Sheath (Schwann cell)", "髄鞘（シュワン細胞）", (709, 291, 804, 323)),
            ("Axon hillock", "軸索小丘", (433, 315, 525, 334)),
            ("Nucleus", "核", (25, 329, 104, 347)),
            ("Nucleolus", "核小体", (10, 348, 85, 366)),
            ("Membrane", "細胞膜", (6, 368, 88, 386)),
            ("Microtubule ", "微小管", (0, 388, 86, 405)),
            ("Mitochondrion", "ミトコンドリア", (39, 423, 146, 441)),
            ("Smooth ER", "滑面小胞体", (79, 456, 162, 474)),
            ("Synapse (Axodendritic)", "シナプス（軸索－樹状突起間）", (57, 519, 139, 551)),
            ("Nucleus (Schwann cell)", "核（シュワン細胞）", (558, 354, 629, 385)),
            ("Microfilament", "ミクロフィラメント", (645, 467, 744, 487)),
            ("Microtubule  ", "微小管", (645, 490, 736, 507)),
            ("Axon", "軸索", (645, 511, 689, 529)),
            ("Dendrites ", "樹状突起", (473, 526, 557, 544)),
        ],
    },
    "hen": {
        "file": "Anatomy_and_physiology_of_animals_Stomach_&_small_intestine_of_hen.jpg", "name": "鶏の胃と小腸（模式図）",
        "labels": [
            ("oesophagus", "食道", (434, 35, 527, 55)),
            ("crop", "そ嚢（嗉嚢）", (431, 114, 470, 131)),
            ("true stomach", "腺胃（真胃）", (49, 163, 146, 180)),
            ("gizzard", "筋胃", (460, 187, 519, 206)),
            ("duodenum", "十二指腸", (16, 250, 98, 267)),
            ("pancreas", "膵臓", (503, 260, 575, 277)),
        ],
    },
    # ---- 第3弾（犬の図） ----
    "forelimb": {
        "file": "Forelimb_dog_corrected.JPG", "name": "犬の前肢の骨（ラベル修正版）",
        "labels": [
            ("humerus", "上腕骨", (292, 74, 361, 91)),
            ("ulna", "尺骨", (5, 168, 44, 185)),
            ("radius", "橈骨", (267, 192, 318, 209)),
            ("carpals", "手根骨", (212, 287, 271, 307)),
            ("metacarpals", "中手骨", (71, 326, 163, 346)),
            ("digits", "指骨", (296, 373, 342, 392)),
        ],
    },
    "hindlimb": {
        "file": "Hind_limb_dog_corrected.JPG", "name": "犬の後肢の骨（ラベル修正版）",
        "labels": [
            ("femur", "大腿骨", (87, 49, 137, 66)),
            ("patella", "膝蓋骨", (350, 132, 405, 152)),
            ("fibula", "腓骨", (87, 169, 134, 186)),
            ("tibia", "脛骨", (317, 199, 356, 216)),
            ("tarsals", "足根骨", (193, 293, 249, 310)),
            ("metatarsals", "中足骨", (30, 331, 118, 348)),
            ("digits", "趾骨", (241, 384, 287, 402)),
        ],
    },
    "repro": {
        "file": "Female_repro_system_labelled.JPG", "name": "雌犬の生殖器",
        "labels": [
            ("uterus", "子宮", (242, 7, 294, 23)),
            ("fallopian tube", "卵管", (7, 105, 99, 125)),
            ("ovary", "卵巣", (201, 130, 249, 145)),
            ("uterus ", "子宮", (319, 143, 371, 159)),
            ("cervix", "子宮頸", (319, 166, 369, 182)),
            ("vagina", "腟", (318, 196, 373, 212)),
            ("opening of urethra", "外尿道口", (318, 243, 451, 263)),
            ("vulva", "外陰部", (318, 278, 364, 295)),
        ],
    },
    "rumen": {
        "file": "Anatomy_and_physiology_of_animals_The_rumen.jpg", "name": "反芻動物（牛など）の胃（模式図）",
        "labels": [
            ("oesophagus", "食道", (244, 21, 337, 41)),
            ("omasum", "第三胃", (111, 97, 179, 111)),
            ("abomasum", "第四胃", (94, 165, 179, 182)),
            ("to small intestine", "小腸へ", (38, 267, 105, 302)),
            ("reticulum", "第二胃", (334, 287, 405, 304)),
            ("rumen", "第一胃", (451, 290, 504, 304)),
        ],
    },
    # 古い教科書の図は図中の記号（a, b, 9 …）と凡例で示されている。記号の位置に同じ記号の丸を重ねる（位置は原画像の座標）
    "brain3": {
        "file": "A_text-book_of_veterinary_anatomy_(Page_724)_BHL18587848.jpg", "name": "犬の脳の底面（Sisson の獣医解剖学書 Fig.539）",
        "page_crop": (180, 1150, 1250, 2380), "r": 30,
        "markers": [
            ("a", (567, 1382), "嗅球", "Olfactory bulb"), ("b", (620, 1717), "視神経", "optic nerve"),
            ("4", (635, 1792), "灰白隆起と漏斗", "tuber cinereum and infundibulum"), ("5", (498, 1792), "梨状葉", "pyriform lobe"),
            ("9", (686, 2086), "橋", "pons"), ("10", (683, 2223), "延髄", "medulla oblongata"),
            ("11", (897, 2213), "小脳", "cerebellum"), ("12", (695, 1919), "大脳脚", "cerebral peduncle"),
        ],
    },
    "muscles": {
        "file": "A_text-book_of_veterinary_anatomy_(Page_319)_BHL18587443.jpg", "name": "犬の浅層の筋（Sisson の獣医解剖学書 Fig.230）",
        "page_crop": (150, 950, 2400, 2090), "r": 46,
        "markers": [
            ("e", (1468, 1319), "僧帽筋", "trapezius"), ("f", (1328, 1320), "僧帽筋", "trapezius"),
            ("i", (1178, 1444), "広背筋", "latissimus dorsi"), ("o", (1448, 1605), "上腕三頭筋（長頭）", "triceps, long head"),
            ("29", (777, 1970), "前脛骨筋", "tibialis anterior"), ("33", (632, 1862), "腓腹筋", "gastrocnemius"),
            ("25", (1757, 1444), "頸静脈", "jugular vein"),
        ],
    },
    "placenta": {
        "file": "PlacZonaireRailliet1895MeyCh.jpg", "name": "犬の胎子と胎膜（Railliet 1895）",
        "page_crop": (0, 0, 996, 418), "r": 21,
        "markers": [
            ("a", (546, 37), "帯状胎盤", "placenta zonaire"), ("a", (531, 357), "帯状胎盤", "placenta zonaire"),
            ("b", (450, 33), "帯状胎盤", "placenta zonaire"), ("b", (627, 53), "帯状胎盤", "placenta zonaire"),
            ("b", (486, 375), "帯状胎盤", "placenta zonaire"), ("b", (574, 375), "帯状胎盤", "placenta zonaire"),
            ("c", (286, 46), "絨毛膜", "chorion"), ("c", (737, 95), "絨毛膜", "chorion"), ("c", (844, 339), "絨毛膜", "chorion"),
            ("d", (113, 287), "羊膜", "amnios"), ("d", (797, 315), "羊膜", "amnios"),
        ],
    },
    # 骨格図は番号と凡例が最初から付いている（番号＝凡例の番号）
    "skeleton": {
        "file": "Skeleton_of_a_dog_diagram.svg", "name": "犬の骨格", "svg": True,
        # 橈骨と尺骨、脛骨と腓骨は、番号の点がどちらの骨を指すか図から読み取りにくいので、場所の説明には使わない
        "unsure": ["9", "10", "21", "22"],
        "legend": {
            1: ("Cranium, or Skull", "頭蓋"), 2: ("Maxilla", "上顎骨"), 3: ("Mandible, or Lower jaw", "下顎骨"), 4: ("Atlas", "環椎"),
            5: ("Axis", "軸椎"), 6: ("Scapula, or Shoulder-blade", "肩甲骨"), 7: ("Spine of scapula", "肩甲棘"), 8: ("Humerus", "上腕骨"),
            9: ("Radius", "橈骨"), 10: ("Ulna", "尺骨"), 11: ("Phalanges", "指骨"), 12: ("Metacarpal Bones", "中手骨"),
            13: ("Carpal Bones or Wrist-bones", "手根骨"), 14: ("Sternum, or Breast-bone", "胸骨"), 15: ("Cartilaginous part of rib", "肋軟骨"),
            16: ("Ribs (13 in number)", "肋骨"), 17: ("Phalanges", "趾骨"), 18: ("Metatarsal Bones", "中足骨"), 19: ("Tarsal Bones", "足根骨"),
            20: ("Calcaneus (os calcu)", "踵骨"), 21: ("Fibula", "腓骨"), 22: ("Tibia", "脛骨"), 23: ("Patella, or Knee-cap", "膝蓋骨"),
            24: ("Femur", "大腿骨"), 25: ("Ischium", "坐骨"), 26: ("Pelvis, or Hip-bone", "寛骨"),
            "A": ("Cervical or Neck Bones (7 in number)", "頸椎"), "B": ("Dorsal or Thoracic Bones (13 in number, each bearing a rib)", "胸椎"),
            "C": ("Lumbar Bones (7 in number)", "腰椎"), "D": ("Sacral Bones (3 in number)", "仙椎"), "E": ("Caudal or Tail Bones (20 to 23 in number)", "尾椎"),
        },
    },
}
SCALE = 2  # 小さい教科書図は2倍に拡大してから番号を描く


CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def chrome_png(svg, size, strip_text=False):
    """SVG を Chrome で2倍の解像度の PNG にする（PyMuPDF では崩れる図があるため）。
    strip_text: ラベルが図に重なっていて塗りつぶせない図は、SVG の文字要素を消してから描く"""
    out = SRC / f"_c2_{Path(svg).stem}{'_notext' if strip_text else ''}.png"
    if not out.exists():
        tmp = Path(tempfile.mkdtemp())
        if strip_text:
            body = re.sub(r"<text\b.*?</text>", "", (SRC / svg).read_text(encoding="utf-8"), flags=re.S)
            svg = tmp / "s.svg"
            svg.write_text(body, encoding="utf-8")
        # Chrome は書き出し後に終了しないことがあるので、perl の alarm で打ち切る
        subprocess.run(["perl", "-e", "alarm 30; exec @ARGV", CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--lang=en-US",
                        f"--user-data-dir={tmp}/u", "--hide-scrollbars", "--force-device-scale-factor=2", f"--window-size={size[0]},{size[1]}",
                        f"--screenshot={tmp}/o.png", f"file://{SRC / svg}"], capture_output=True)
        shutil.copy(tmp / "o.png", out)
    return Image.open(out).convert("RGB")


def bgcolor(arr, x0, y0, x1, y1):
    """ラベルの周りの色（枠の画素の中央値）。色付きの背景でも違和感なく消せるようにする。"""
    h, w = arr.shape[:2]
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, w - 1), min(y1, h - 1)
    edge = np.concatenate([arr[y0, x0:x1], arr[y1, x0:x1], arr[y0:y1, x0], arr[y0:y1, x1]])
    return tuple(int(v) for v in np.median(edge, axis=0))


def masked(fig):
    if fig.get("chrome"):
        im = chrome_png(fig["file"], fig["chrome"], fig.get("strip_text", False))
        W = im.width // SCALE
    else:
        im = Image.open(SRC / fig.get("img", fig["file"])).convert("RGB")
        W = im.width
        im = im.resize((im.width * SCALE, im.height * SCALE), Image.LANCZOS)
    arr = np.asarray(im).copy()
    d = ImageDraw.Draw(im)
    rr = fig.get("r", 12)  # 番号の丸の半径（等倍）。ラベルが密な図は小さくする
    font = ImageFont.truetype(FONT, round(rr * 13 / 12 * SCALE))
    jfont = ImageFont.truetype(JFONT, 12 * SCALE)
    labels = fig["labels"]
    # 番号は上から順（同じ高さなら左から）
    band = fig.get("band", 30)
    order = sorted(range(len(labels)), key=lambda i: ((labels[i][2][1] + labels[i][2][3]) // band, labels[i][2][0]))
    num = {i: k + 1 for k, i in enumerate(order)}
    for i, (_, _, r, *_) in enumerate(labels):
        if fig.get("strip_text"):
            break
        x0, y0, x1, y1 = (v * SCALE for v in r)
        d.rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), fill=bgcolor(arr, x0 - 3, y0 - 3, x1 + 3, y1 + 3))
    for i, (_, _, r, *side) in enumerate(labels):
        x0, y0, x1, y1 = (v * SCALE for v in r)
        cx = (r[0] + r[2]) / 2
        # 引き出し線がつながる側（図の中心に近い側）に番号を置く。side で "R"/"L" を指定もできる
        off = (rr + 1) * SCALE
        if side:
            x = x1 - off if side[0] == "R" else x0 + off if side[0] == "L" else (x0 + x1) / 2
        elif r[2] - r[0] < 40:
            x = (x0 + x1) / 2
        elif cx < W / 2:
            x = x1 - off
        else:
            x = x0 + off
        y = (y0 + y1) / 2
        R = rr * SCALE
        d.ellipse((x - R, y - R, x + R, y + R), fill=PINK, outline="white", width=2 * SCALE)
        d.text((x, y + 1), str(num[i]), font=font, fill="white", anchor="mm")
    for text, r in fig.get("captions", []):
        x0, y0, x1, y1 = (v * SCALE for v in r)
        d.rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), fill=bgcolor(arr, x0 - 3, y0 - 3, x1 + 3, y1 + 3))
        d.text(((x0 + x1) / 2, (y0 + y1) / 2), text, font=jfont, fill=(40, 40, 40), anchor="mm")
    if "crop" in fig:
        im = im.crop(tuple(v * SCALE for v in fig["crop"]))
    keys = {labels[i][0]: {"n": num[i], "ja": labels[i][1]} for i in range(len(labels))}
    return im, keys


def marked(fig):
    """図中の記号の位置に、同じ記号のピンクの丸を重ねる（記号の意味は原典の凡例どおり）。"""
    im = Image.open(SRC / fig["file"]).convert("RGB")
    ox, oy = fig["page_crop"][:2]
    im = im.crop(fig["page_crop"])
    sc = 2 if im.width < 1200 else 1
    if sc > 1:
        im = im.resize((im.width * sc, im.height * sc), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    R = fig["r"] * sc
    font = ImageFont.truetype(FONT, round(R * 1.1))
    keys = {}
    for sym, (x, y), ja, en in fig["markers"]:
        x, y = (x - ox) * sc, (y - oy) * sc
        d.ellipse((x - R, y - R, x + R, y + R), fill=PINK, outline="white", width=max(2, R // 6))
        d.text((x, y + 1), sym, font=font, fill="white", anchor="mm")
        keys[sym] = {"n": sym, "ja": ja, "en": en}
    return im, keys


def skeleton(fig):
    doc = fitz.open(SRC / fig["file"])
    pix = doc[0].get_pixmap(dpi=96)  # 1052x744 → 約1000px幅
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    keys = {str(k): {"n": k, "ja": v[1], "en": v[0]} for k, v in fig["legend"].items()}
    return im, keys


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = json.loads((SRC / "meta.json").read_text())
    figs = {}
    for fid, fig in FIGS.items():
        im, keys = skeleton(fig) if fig.get("svg") else marked(fig) if fig.get("markers") else masked(fig)
        if im.width > 1000:
            im = im.resize((1000, round(im.height * 1000 / im.width)), Image.LANCZOS)
        im.save(OUT / f"{fid}.webp", "WEBP", quality=82)
        m = meta[fig["file"]]
        if "Lawson" in m["description"] and "Otago" in m["description"]:  # Commons の Artist 欄はアップロード者なので、説明欄の作者名を使う
            m = {**m, "artist": "Ruth Lawson（Otago Polytechnic）"}
        if "Sisson" in m["artist"]:
            m = {**m, "artist": "Septimus Sisson『A text-book of veterinary anatomy』（図の原典は Ellenberger）"}
        figs[fid] = {"name": fig["name"], "img": f"data/figs/{fid}.webp", "keys": keys,
                     "credit": {"title": m["title"].replace("File:", ""), "author": m["artist"].split("\n")[0].strip(),
                                "license": m["license"], "license_url": m["license_url"], "url": m["page"],
                                "note": "改変なし（凡例を日本語訳）" if fig.get("svg") else "図を切り抜き、図中の記号に色の丸を重ねて表示（記号の意味は原典の凡例による）" if fig.get("markers") else "英語ラベルを番号に置き換えて改変"}}
        print(fid, im.size, len(keys))
    qsrc = SRC / "fig_questions.json"
    questions = build_questions(json.loads(qsrc.read_text()), figs) if qsrc.exists() else []
    (ROOT / "app" / "data" / "figs.json").write_text(json.dumps({"figs": figs, "questions": questions}, ensure_ascii=False, indent=1))
    print("questions", len(questions))


CIRC = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿"


def mark(n):
    return CIRC[n - 1] if isinstance(n, int) else n


def build_questions(src, figs):
    out = []
    for no, (qid, q) in enumerate(src.items(), 1):
        f = figs[q["fig"]]
        keys = f["keys"]
        tgt = keys[q["target"]]
        fill = lambda t: t.replace("{n}", mark(tgt["n"]))
        stem = fill(q["stem"])
        if q["kind"] == "term":      # 「図の③はどれか」→ 日本語名から選ぶ
            opts = [keys[k] for k in q["options"]] if "options" in q else None
            choices = [o["ja"] for o in opts] if opts else q["choices"]
            answer = choices.index(tgt["ja"]) + 1 if opts else q["answer"]
            where = {o["ja"]: o["n"] for o in opts} if opts else {}
        elif q["kind"] == "num":     # 「小脳はどれか」→ 番号から選ぶ
            opts = [keys[k] for k in q["options"]]
            choices = [mark(o["n"]) for o in opts]
            answer = q["options"].index(q["target"]) + 1
            where = {}
        else:                        # 選択肢を直接書く問題（役割を問うなど）。図にある名前なら場所も示す
            choices, answer, opts = q["choices"], q["answer"], None
            where = {}
            for k in keys.values():
                where.setdefault(k["ja"], k["n"])
        # 正答の位置が偏らないよう、問題ごとに決まった並びにシャッフル
        perm = list(range(len(choices)))
        random.Random(qid).shuffle(perm)
        choices = [choices[i] for i in perm]
        if opts:
            opts = [opts[i] for i in perm]
        answer = perm.index(answer - 1) + 1
        unsure = {keys[k]["ja"] for k in FIGS[q["fig"]].get("unsure", [])}
        where = {k: v for k, v in where.items() if k not in unsure}
        expl_choices = []
        for i, c in enumerate(choices):
            if i + 1 == answer:
                expl_choices.append("正答。" + fill(q.get("why", "")))
            elif q["kind"] == "num":
                expl_choices.append(f"正答ではありません。{c}は{opts[i]['ja']}です。")
            elif c in q.get("notes", {}):
                expl_choices.append("正答ではありません。" + q["notes"][c])
            elif c in where:
                expl_choices.append(f"正答ではありません。{c}は図の{mark(where[c])}です。")
            else:
                expl_choices.append("正答ではありません。")
        out.append({
            "id": "fig-" + qid, "genre": "fig", "level": q.get("level", 2), "fig": q["fig"],
            "examName": "図で覚える", "section": f["name"], "no": no,
            "stem": stem, "choices": choices, "answer": [answer],
            "source": {"title": "図：" + f["credit"]["title"], "publisher": f"{f['credit']['author']}／{f['credit']['license']}（{f['credit']['note']}）", "url": f["credit"]["url"]},
            "explanation": {"summary": fill(q["summary"]), "choices": expl_choices, "point": q.get("point", ""), "refs": q["refs"], "checked": q["checked"]},
            "related": q.get("related", []),
        })
    return out


if __name__ == "__main__":
    main()
