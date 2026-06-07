#!/usr/bin/env python3
"""
调整数据集采样比例工具

功能：
1. 读取数据集JSON文件，获取每个数据集的帧数
2. 按关键词将数据集分组，设置每组的frame采样总占比
3. 确保同一组内的每个数据集frame采样比例相同
4. 输出调整后的采样权重

Frame采样比例 = (frame数 * 采样权重) / Σ(frame数 * 采样权重)

使用方法：
    1. 修改下方配置区域的参数
    2. python adjust_sampling_ratio.py
"""

import json
from pathlib import Path
from typing import Dict, List

# ============================================================================
# 配置区域
# ============================================================================

# 输入/输出文件路径
# INPUT_JSON = "/mnt/vepfs01/output/yifeng/resources/frontdesk/20260316_pi05_cctv_SkewerFruits_v3v4_group.json"
INPUT_JSON = "/mnt/vepfs01/output/yifeng/resources/frontdesk/20260428_20260126_pi05_base_32_iter050000_resume.json"
# OUTPUT_JSON = "/mnt/vepfs01/output/yifeng/resources/frontdesk/20260316_pi05_cctv_SkewerFruits_v3v4_group.json"
OUTPUT_JSON = "/mnt/vepfs01/output/yifeng/resources/frontdesk/20260428_20260126_pi05_base_32_iter050000_resume.json"
# 分组规则：{组名: 关键词} 或 {组名: [关键词列表]}
# GROUP_RULES = {
#     "human_interaction": "Humaninteraction",
#     "pick_place": ["v6_FrontDeskDemo/851_20251208_NoReset_VisualPrompt_PickPlace", "202510_all_dual", "pickplace_visualprompt_09vpALL"],
#     "writing_desk_vp": ["1000_20251225_Pick&PlaceEverything_Visual_Prompt","1011_20251228_Pick&PlaceEverything_VisualPrompt","1026_20251230_PickPlaceEverythingWithBookshelf_VisualPrompt"],
#     "writing_desk_scoop": ["1014_20251228_ScoopNuts"],
#     "writing_desk_penholder": ["1015_20251228_PenHolder"],
#     "writing_desk_bookwithbookend": ["1028_20251231_BookWithBookend_VisualPrompt"]
# }

# GROUP_RULES = {
#     "human_interaction": "Humaninteraction",
#     "pick_place": ["v6_FrontDeskDemo/851_20251208_NoReset_VisualPrompt_PickPlace", "202510_all_dual", "pickplace_visualprompt_09vpALL"],
#     "drawer": ["drawer"],
#     "insert": ["Insert_V2","insertflower"],
#     "insert_dagger": ["Insert_dagger","Insertflower_dagger"],
#     "makesandwich": ["Makesandwich"],
#     "stack": ["Stack"],
#     "waterflowers": ["WaterFlower"],
#     "PourWater": ["PourWater"],
#     "sweep": ["sweep"],
#     "TossToyIntoBox": ["TossToyIntoBox"]
# }


# GROUP_RULES = {
#     "human_interaction": "Humaninteraction",
#     "pick_place": ["v6_FrontDeskDemo/851_20251208_NoReset_VisualPrompt_PickPlace", "202510_all_dual", "pickplace_visualprompt_09vpALL","WB_pp_reset"],
#     "drawer": ["drawer"],
#     "insert": ["Insert_V2","insertflower"],
#     "insert_dagger": ["Insert_dagger","Insertflower_dagger"],
#     "makesandwich": ["Makesandwich"],
#     "stack": ["Stack"],
#     "waterflowers": ["WaterFlower"],
#     "PourWater": ["PourWater"],
#     "sweep": ["sweep"],
#     "TossToyIntoBox": ["TossToyIntoBox"],
#     "wipe_new": ["wipe_new"],
# }




# GROUP_RULES = {
#     "human_interaction": "Humaninteraction",
#     "pick_place": ["v6_FrontDeskDemo/851_20251208_NoReset_VisualPrompt_PickPlace", "202510_all_dual", "pickplace_visualprompt_09vpALL"],
#     "drawer": ["drawer"],
#     "insert": ["Insert_V2","insertflower"],
#     "insert_dagger": ["Insert_dagger","Insertflower_dagger"],
#     "makesandwich": ["Makesandwich"],
#     "stack": ["Stack"],
#     "waterflowers": ["WaterFlower"],
#     "PourWater": ["PourWater"],
#     "sweep": ["sweep"],
#     "TossToyIntoBox": ["TossToyIntoBox"],
#     "writing_desk_vp": ["1000_20251225_Pick&PlaceEverything_Visual_Prompt","1011_20251228_Pick&PlaceEverything_VisualPrompt","1026_20251230_PickPlaceEverythingWithBookshelf_VisualPrompt"],
#     "writing_desk_scoop": ["1014_20251228_ScoopNuts"],
#     "writing_desk_penholder": ["1015_20251228_PenHolder"],
#     "writing_desk_bookwithbookend": ["1028_20251231_BookWithBookend_VisualPrompt"]
# }




# GROUP_RULES = {
#     "human_interaction": "Humaninteraction",
#     "pick_place": ["v6_FrontDeskDemo/851_20251208_NoReset_VisualPrompt_PickPlace", "202510_all_dual", "pickplace_visualprompt_09vpALL","WB_pp_reset"],
#     "drawer": ["drawer"],
#     "insert": ["Insert_V2","insertflower"],
#     "insert_dagger": ["Insert_dagger","Insertflower_dagger"],
#     "makesandwich": ["Makesandwich"],
#     "stack": ["Stack"],
#     "waterflowers": ["WaterFlower"],
#     "PourWater": ["PourWater"],
#     "sweep": ["sweep"],
#     "TossToyIntoBox": ["TossToyIntoBox"],
#     "wipe_new": ["wipe_new"],
#     "writing_desk_vp": ["1000_20251225_Pick&PlaceEverything_Visual_Prompt","1011_20251228_Pick&PlaceEverything_VisualPrompt","1026_20251230_PickPlaceEverythingWithBookshelf_VisualPrompt"],
#     "writing_desk_scoop": ["1014_20251228_ScoopNuts"],
#     "writing_desk_penholder": ["1015_20251228_PenHolder"],
#     "writing_desk_bookwithbookend": ["1028_20251231_BookWithBookend_VisualPrompt"],
#     "dagger_book": ["1073_20260109_writingdesk_v1_book_WBWB_dagger"],
#     "dagger_pp": ["1078_20260109_writingdesk_v1_pickbowlplate_WBWB_dagger"],
#     "scoop_human": ["1076_20260109_ScoopNutsHuman_WritingDesk_FrontDeskDemo_Moz1WB_moz1"],
#     "scoop_new": ["1077_20260109_ScoopNuts_WritingDesk_FrontDeskDemo_Moz1WB_moz1"],
#     "ScoopNutsTwoHands": ["1090_20260112_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB"],
#     "AdjustBowlPosition": ["1091_20260112_AdjustBowlPosition_WritingDesk_FrontDeskDemo"],
#     "WipeSpillArea": ["1098_20260112_WipeSpillArea_WritingDesk_FrontDeskDemo"],
#     "PickStackedBowls": ["1099_20260112_PickStackedBowls_WritingDesk_FrontDeskDemo"],
# }




# GROUP_RULES = {
#     "human_interaction": "Humaninteraction",
#     "pick_place": ["v6_FrontDeskDemo/851_20251208_NoReset_VisualPrompt_PickPlace", "202510_all_dual", "pickplace_visualprompt_09vpALL","WB_pp_reset"],
#     "drawer": ["drawer"],
#     "insert": ["Insert_V2","insertflower","PlaceTableware","PlaceFlatware"],
#     "insert_dagger": ["Insert_dagger","Insertflower_dagger"],
#     "makesandwich": ["Makesandwich"],
#     "stack": ["Stack"],
#     "waterflowers": ["WaterFlower"],
#     "PourWater": ["PourWater"],
#     "sweep": ["sweep"],
#     "TossToyIntoBox": ["TossToyIntoBox"],
#     "candy": ["candy"],
#     "wipe_new": ["wipe_new","Wipe"],
#     "PourTrash": ["PourTrash"],
#     "writing_desk_vp": ["1000_20251225_Pick&PlaceEverything_Visual_Prompt","1011_20251228_Pick&PlaceEverything_VisualPrompt",
#                         "1026_20251230_PickPlaceEverythingWithBookshelf_VisualPrompt","20260109_PickPlaceEverythingWithBookshelf_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
#                         "20260110_ObstacleAvoidingPickPlaceEverythingWithBookshelf_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB_V2",
#                         "20260113_PickPlaceEverythingWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB",
#                         "1165_20260116_DrawerOpened_PickPlaceEverythingWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB","PickPlaceEverythingWithBookshelf_WritingDesk",
#                         "PickPlaceBookWithBookshelf_WritingDesk","MoveObjectWithBookshelf_WritingDesk",
#                         "DrawerOpenedPickPlaceEverythingWithBookshelf_WritingDesk",
#                         "ObstacleAvoidingPickPlaceEverythingWithBookshelf_VisualPrompt_WritingDesk",
#                         "MovePen_WritingDesk"],
#     "writing_desk_scoop": ["1014_20251228_ScoopNuts","1076_20260109_ScoopNutsHuman_WritingDesk_FrontDeskDemo_Moz1WB",
#                             "1077_20260109_ScoopNuts_WritingDesk_FrontDeskDemo_Moz1WB","1090_20260112_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB",
#                             "1168_20260116_DrawerOpened_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB",
#                             "1239_20260125_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB","ScoopNutsTwoHands_WritingDesk","BowlScoopNutsTwoHands_WritingDesk"],
#     "writing_desk_penholder": ["1015_20251228_PenHolder","PenHolder_WritingDesk"],
#     "writing_desk_bookwithbookend": ["1028_20251231_BookWithBookend_VisualPrompt","20251212_Book_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
#                                     "20251225_Book_VisualPrompt_NewWritingDesk_FrontDeskDemo_Moz1WB","20251228_Book_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
#                                     "1138_20260114_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
#                                     "1146_20260114_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
#                                     "20260116_DrawerOpened_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
#                                     "1186_20260119_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
#                                     "1215_20260122_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
#                                     "BookWithBookend_VisualPrompt", "Bookend_VisualPrompt_WritingDesk"],
#     "dagger_book": ["1073_20260109_writingdesk_v1_book_WBWB_dagger","1170_20260115_writingdesk_v1_takebook_WBWB_dagger"],
#     "dagger_pp": ["1078_20260109_writingdesk_v1_pickbowlplate_WBWB_dagger"],
#     "scoop_tea": ["20251216_ScoopTea_FrontDeskDemo_Moz1WB"],
#     "AdjustBowlPosition": ["1091_20260112_AdjustBowlPosition_WritingDesk_FrontDeskDemo"],
#     "WipeSpillArea": ["1098_20260112_WipeSpillArea_WritingDesk_FrontDeskDemo","20260113_WipeSpillArea_WritingDesk_FrontDeskDemo"],
#     "PickStackedBowls": ["1099_20260112_PickStackedBowls_WritingDesk_FrontDeskDemo"],
#     "PrepareForSnack": ["20251218_PrepareForSnack_FrontDeskDemo_Moz1WB"],
#     "PenHolder": ["20251218_PenHolder_FrontDeskDemo_Moz1WB"],
#     "tie_knot": ["1151_20260115_TieKnot__Moz1WB"],
#     "twist_bottle_cap": ["20260122_TwistBottleCap_Moz1WB"],
#     "cocktail": ["Cocktail","CupName_PromptReseach_Demo","CocktailUmbrella_PromptReseach_Demo"],
#     "basketball": ["basketball"],
#     "SkewerFruits": ["SkewerFruits","CupUpright"],
# }

# 0428 no_reset 书桌demo - 简化版（只针对当前6个数据集，提高插笔比例）
# 说明：1086 和 1384 插笔动作更多，单独分组给更高权重
GROUP_RULES = {
    # 插笔动作多的数据集（1086 的两个 dataset + 1384 的一个 dataset）
    "desk_penholder_rich": ["1086_20260109_PickPlaceEverythingWithBookshelf", "1384_20260203_MoveObjectWithBookshelf"],
    # 普通 pick&place 数据集（1011 的两个 dataset + 1026 的一个 dataset）
    "desk_pickplace": ["1011_20251228_Pick&PlaceEverything_VisualPrompt", "1026_20251230_PickPlaceEverythingWithBookshelf_VisualPrompt"],
}







# GROUP_RULES = {
#     # "human_interaction": "Humaninteraction",
#     # "pick_place": ["v6_FrontDeskDemo/851_20251208_NoReset_VisualPrompt_PickPlace", "202510_all_dual", "pickplace_visualprompt_09vpALL"],
#     "writing_desk_vp": ["1000_20251225_Pick&PlaceEverything_Visual_Prompt","1011_20251228_Pick&PlaceEverything_VisualPrompt","1026_20251230_PickPlaceEverythingWithBookshelf_VisualPrompt"],
#     "writing_desk_scoop": ["1014_20251228_ScoopNuts"],
#     "writing_desk_penholder": ["1015_20251228_PenHolder"],
#     "writing_desk_bookwithbookend": ["1028_20251231_BookWithBookend_VisualPrompt"],
#     "dagger_book": ["1073_20260109_writingdesk_v1_book_WBWB_dagger"],
#     "dagger_pp": ["1078_20260109_writingdesk_v1_pickbowlplate_WBWB_dagger"],
#     "scoop_human": ["1076_20260109_ScoopNutsHuman_WritingDesk_FrontDeskDemo_Moz1WB_moz1"],
#     "scoop_new": ["1077_20260109_ScoopNuts_WritingDesk_FrontDeskDemo_Moz1WB_moz1"],
# }


# 各组的配置：(比例值, power_alpha) 或 (比例值, power_alpha, is_fixed)
# - 比例值：
#   - 如果 is_fixed=True：该组的最终固定占比（如 0.1 表示固定占10%）
#   - 如果 is_fixed=False 或省略：用于归一化的相对数值
#   - 所有 "相对数值" 的组会分享 (1 - 固定占比之和) 的剩余比例
#   - 注意：所有在 GROUP_RULES 中定义的组都必须在这里配置
# - power_alpha：控制组内分配方式
#   - alpha = 1.0：组内每个数据集的 frame 采样比例完全相同
#   - alpha = 0.0：组内按帧数比例采样（帧数多的数据集采样更多）
#   - 0 < alpha < 1：平衡两者，避免小数据集权重过高
# - is_fixed（可选）：True 表示固定占比，False 或省略表示相对数值
#
# 示例：
#   "group_a": (0.1, 1.0, True),   # 固定占比 10%
#   "group_b": (2, 0.7),           # 相对数值 2，与其他相对组分享剩余 90%
#   "group_c": (1, 0.7),           # 相对数值 1
#   # group_b 和 group_c 按 2:1 分配 90%，即 group_b=60%, group_c=30%


# GROUP_CONFIG = {
#     "human_interaction": (0.05, 1.0),
#     "pick_place": (0.15, 0.7),
#     "writing_desk_vp": (0.2, 0.7),
#     "writing_desk_scoop": (0.2, 0.7),
#     "writing_desk_penholder": (0.2, 0.7),
#     "writing_desk_bookwithbookend": (0.2, 0.7),
#     # "writing_desk": (0.8, 1.0),        # 占比80%
# }

# GROUP_CONFIG = {
#     "human_interaction": (0.1, 1.0),
#     "pick_place": (0.30, 0.7),
#     "drawer": (0.6/8, 1.0),
#     "insert": (0.3/8, 1.0),
#     "insert_dagger": (0.3/8, 1.0),
#     "makesandwich": (0.6/8, 1.0),
#     "stack": (0.6/8, 1.0),
#     "waterflowers": (0.6/8, 1.0),
#     "PourWater": (0.6/8, 1.0),
#     "sweep": (0.6/8, 1.0),
#     "TossToyIntoBox": (0.6/8, 1.0),
# }


# GROUP_CONFIG = {
#     "human_interaction": (0.05, 1.0, True),
#     "pick_place": (0.15, 0.7, True),
#     "drawer": (1, 1.0),
#     "insert": (0.5, 1.0),
#     "insert_dagger": (0.5, 1.0),
#     "makesandwich": (1, 1.0),
#     "stack": (1, 1.0),
#     "waterflowers": (1, 1.0),
#     "PourWater": (1, 1.0),
#     "sweep": (1, 1.0),
#     "TossToyIntoBox": (1, 1.0),
#     "wipe_new": (1, 1.0),
# }


# GROUP_CONFIG = {
#     "human_interaction": (1, 1.0),
#     "pick_place": (0.1, 0.7, True),
#     "drawer": (1.5, 1.0),
#     "insert": (1, 1.0),
#     "insert_dagger": (1, 1.0),
#     "makesandwich": (1, 1.0),
#     "stack": (1, 1.0),
#     "waterflowers": (1, 1.0),
#     "PourWater": (1, 1.0),
#     "sweep": (1, 1.0),
#     "TossToyIntoBox": (1, 1.0),
#     "writing_desk_vp": (1, 0.7),
#     "writing_desk_scoop": (1, 0.7),
#     "writing_desk_penholder": (1, 0.7),
#     "writing_desk_bookwithbookend": (1.5, 0.7),
# }


# GROUP_CONFIG = {
#     "human_interaction": (0.05, 1.0, True),
#     "pick_place": (0.15, 0.7, True),
#     "drawer": (1.5, 1.0),
#     "insert": (1, 1.0),
#     "insert_dagger": (1, 1.0),
#     "makesandwich": (1, 1.0),
#     "stack": (1, 1.0),
#     "waterflowers": (1, 1.0),
#     "PourWater": (1, 1.0),
#     "sweep": (1, 1.0),
#     "TossToyIntoBox": (1, 1.0),
#     "wipe_new": (1, 1.0),
#     "writing_desk_vp": (1, 0.7),
#     "writing_desk_scoop": (1, 0.7),
#     "writing_desk_penholder": (1, 0.7),
#     "writing_desk_bookwithbookend": (1, 0.7),
#     "dagger_book": (1, 1.0),
#     "dagger_pp": (1, 1.0),
#     "scoop_human": (1, 1.0),
#     "scoop_new": (1, 1.0),
#     "ScoopNutsTwoHands": (1, 1.0),
#     "AdjustBowlPosition": (1, 1.0),
#     "WipeSpillArea": (1, 1.0),
#     "PickStackedBowls": (1, 1.0),
# }




# GROUP_CONFIG = {
#     "human_interaction": (1, 0.57),
#     "pick_place": (2, 0.57),
#     "drawer": (1, 0.57),
#     "insert": (2, 0.57),
#     "insert_dagger": (1, 0.57),
#     "makesandwich": (1, 0.57),
#     "stack": (1, 0.57),
#     "waterflowers": (1, 0.57),
#     "PourWater": (1, 0.57),
#     "sweep": (2, 0.57),
#     "TossToyIntoBox": (1, 0.57),
#     "wipe_new": (1, 0.57),
#     "PourTrash": (1, 0.57),
#     "PrepareForSnack": (1, 0.57),
#     "PenHolder": (1, 0.57),
#     "candy": (0.1, 0.57),
#     "writing_desk_vp": (4, 0.57),
#     "writing_desk_scoop": (4, 0.57),
#     "writing_desk_penholder": (2, 0.57),
#     "writing_desk_bookwithbookend": (8, 0.57),
#     "dagger_book": (3, 0.57),
#     "dagger_pp": (0.5, 0.57),
#     "scoop_tea": (0.5, 0.57),
#     "AdjustBowlPosition": (1, 0.57),
#     "WipeSpillArea": (0.5, 0.57),
#     "PickStackedBowls": (0.2, 0.57),
#     "tie_knot": (1, 0.57),
# }


# GROUP_CONFIG = {
#     "writing_desk_scoop": (1, 0.57),
#     "AdjustBowlPosition": (1, 0.57),
# }


# GROUP_CONFIG = {
#     "writing_desk_bookwithbookend": (8, 0.57),
#     # "dagger_book": (3, 0.57),
# }




# GROUP_CONFIG = {
#     # "human_interaction": (0.05, 1.0, True),
#     # "pick_place": (0.15, 0.7, True),
#     "writing_desk_vp": (1, 0.7),
#     "writing_desk_scoop": (1, 0.7),
#     "writing_desk_penholder": (1, 0.7),
#     "writing_desk_bookwithbookend": (1, 0.7),
#     "dagger_book": (1, 1.0),
#     "dagger_pp": (1, 1.0),
#     "scoop_human": (1, 1.0),
#     "scoop_new": (1, 1.0),
# }



# # 0130 cotrain
# GROUP_CONFIG = {
#     "human_interaction": (1, 0.57),
#     "pick_place": (2, 0.57),
#     "drawer": (1, 0.57),
#     "insert": (2, 0.57),
#     "insert_dagger": (1, 0.57),
#     "makesandwich": (1, 0.57),
#     "stack": (1, 0.57),
#     "waterflowers": (1, 0.57),
#     "PourWater": (1, 0.57),
#     "sweep": (2, 0.57),
#     "TossToyIntoBox": (1, 0.57),
#     "wipe_new": (1, 0.57),
#     "PourTrash": (1, 0.57),
#     "PrepareForSnack": (1, 0.57),
#     "PenHolder": (1, 0.57),
#     "candy": (0.1, 0.57),
#     "writing_desk_vp": (4, 0.57),
#     "writing_desk_scoop": (4, 0.57),
#     "writing_desk_penholder": (2, 0.57),
#     "writing_desk_bookwithbookend": (8, 0.57),
#     "dagger_book": (3, 0.57),
#     "dagger_pp": (0.5, 0.57),
#     "scoop_tea": (0.5, 0.57),
#     "AdjustBowlPosition": (1, 0.57),
#     "WipeSpillArea": (0.5, 0.57),
#     "PickStackedBowls": (0.2, 0.57),
#     "tie_knot": (1, 0.57),
#     "cocktail": (0.5, 0.57),
#     "basketball": (0.5, 0.57),
#     "twist_bottle_cap": (0.5, 0.57),
# }




# # # 0203 cotrain
# GROUP_CONFIG = {
#     "human_interaction": (1, 0.57),
#     "pick_place": (2, 0.57),
#     "drawer": (1, 0.57),
#     "insert": (2, 0.57),
#     "insert_dagger": (1, 0.57),
#     "makesandwich": (1, 0.57),
#     "stack": (1, 0.57),
#     "waterflowers": (1, 0.57),
#     "PourWater": (1, 0.57),
#     "sweep": (2, 0.57),
#     "TossToyIntoBox": (1, 0.57),
#     "wipe_new": (1, 0.57),
#     "PourTrash": (1, 0.57),
#     "PrepareForSnack": (1, 0.57),
#     "PenHolder": (1, 0.57),
#     "candy": (0.1, 0.57),
#     "writing_desk_vp": (8, 0.57),
#     "writing_desk_scoop": (1, 0.57),
#     "writing_desk_penholder": (2, 0.57),
#     "writing_desk_bookwithbookend": (1.5, 0.57),
#     "dagger_book": (1, 0.57),
#     "dagger_pp": (1, 0.57),
#     "scoop_tea": (0.5, 0.57),
#     "AdjustBowlPosition": (1, 0.57),
#     "WipeSpillArea": (0.5, 0.57),
#     "PickStackedBowls": (0.2, 0.57),
#     "tie_knot": (1, 0.57),
#     "cocktail": (0.5, 0.57),
#     "basketball": (0.5, 0.57),
#     "twist_bottle_cap": (0.5, 0.57),
# }

# # 0214 cotrain
# GROUP_CONFIG = {
#     "human_interaction": (1, 0.57),
#     "pick_place": (2, 0.57),
#     "drawer": (1, 0.57),
#     "insert": (2, 0.57),
#     "insert_dagger": (1, 0.57),
#     "makesandwich": (1, 0.57),
#     "stack": (1, 0.57),
#     "waterflowers": (1, 0.57),
#     "PourWater": (1, 0.57),
#     "sweep": (2, 0.57),
#     "TossToyIntoBox": (1, 0.57),
#     "wipe_new": (1, 0.57),
#     "PourTrash": (1, 0.57),
#     "PrepareForSnack": (1, 0.57),
#     "PenHolder": (1, 0.57),
#     "candy": (0.1, 0.57),
#     "writing_desk_vp": (8, 0.57),
#     "writing_desk_scoop": (0.5, 0.57),
#     "writing_desk_penholder": (2, 0.57),
#     "writing_desk_bookwithbookend": (0.5, 0.57),
#     "dagger_book": (0.25, 0.57),
#     "dagger_pp": (1, 0.57),
#     "scoop_tea": (0.5, 0.57),
#     "AdjustBowlPosition": (1, 0.57),
#     "WipeSpillArea": (0.5, 0.57),
#     "PickStackedBowls": (0.2, 0.57),
#     "tie_knot": (1, 0.57),
#     "cocktail": (0.5, 0.57),
#     "basketball": (0.5, 0.57),
#     "twist_bottle_cap": (0.5, 0.57),
#     "SkewerFruits": (1, 0.57)
# }



## 0228 reweight
# GROUP_CONFIG = {
#     "human_interaction": (1, 0.57), 14000
#     "pick_place": (2, 0.57),    8000
#     "drawer": (1, 0.57), 14000
#     "insert": (2, 0.57), 12000
#     "insert_dagger": (1, 0.57), 10000
#     "makesandwich": (1, 0.57), 12000
#     "stack": (1, 0.57), 14000
#     "waterflowers": (1, 0.57), 30000
#     "PourWater": (1, 0.57), 14000
#     "sweep": (2, 0.57), 34000
#     "TossToyIntoBox": (1, 0.57), 22000
#     "wipe_new": (1, 0.57),
#     "PourTrash": (1, 0.57), 38000
#     "PrepareForSnack": (1, 0.57), 8000
#     "PenHolder": (1, 0.57), 12000
#     "candy": (0.1, 0.57), 16000
#     "writing_desk_vp": (8, 0.57), 14000
#     "writing_desk_scoop": (0.5, 0.57), 50000
#     "writing_desk_penholder": (2, 0.57), 14000
#     "writing_desk_bookwithbookend": (0.5, 0.57),
#     "dagger_book": (0.25, 0.57),
#     "dagger_pp": (1, 0.57), 4000
#     "scoop_tea": (0.5, 0.57),
#     "AdjustBowlPosition": (1, 0.57), 12000
#     "WipeSpillArea": (0.5, 0.57),
#     "PickStackedBowls": (0.2, 0.57),
#     "tie_knot": (1, 0.57), 14000
#     "cocktail": (0.5, 0.57),
#     "basketball": (0.5, 0.57),
#     "twist_bottle_cap": (0.5, 0.57),
#     "SkewerFruits": (1, 0.57)
# }



# ## 0228 reweight
# GROUP_CONFIG = {
#     "human_interaction": (0.3, 0.57),
#     "pick_place": (0.4, 0.57),
#     "drawer": (0.3, 0.57),
#     "insert": (0.6, 0.57),
#     "insert_dagger": (0.2, 0.57),
#     "makesandwich": (0.25, 0.57),
#     "stack": (0.3, 0.57),
#     "waterflowers": (0.5, 0.57),
#     "PourWater": (0.3, 0.57),
#     "sweep": (1, 0.57),
#     "TossToyIntoBox": (0.5, 0.57),
#     "wipe_new": (1, 0.57),
#     "PourTrash": (0.6, 0.57),
#     "PrepareForSnack": (0.2, 0.57),
#     "PenHolder": (0.25, 0.57),
#     "candy": (0.03, 0.57),
#     "writing_desk_vp": (2.5, 0.57),
#     "writing_desk_scoop": (0.5, 0.57),
#     "writing_desk_penholder": (0.7, 0.57),
#     "writing_desk_bookwithbookend": (0.5, 0.57),
#     "dagger_book": (0.25, 0.57),
#     "dagger_pp": (0.1, 0.57),
#     "scoop_tea": (0.5, 0.57),
#     "AdjustBowlPosition": (0.25, 0.57),
#     "WipeSpillArea": (0.5, 0.57),
#     "PickStackedBowls": (0.2, 0.57),
#     "tie_knot": (0.3, 0.57),
#     "cocktail": (0.5, 0.57),
#     "basketball": (0.5, 0.57),
#     "twist_bottle_cap": (0.5, 0.57),
#     "SkewerFruits": (1, 0.57)
# }



# # 0304 cotrain
# GROUP_CONFIG = {
#     "human_interaction": (1, 0.57),
#     "pick_place": (2, 0.57),
#     "drawer": (1, 0.57),
#     "insert": (2, 0.57),
#     "insert_dagger": (1, 0.57),
#     "makesandwich": (1, 0.57),
#     "stack": (1, 0.57),
#     "waterflowers": (1, 0.57),
#     "PourWater": (1, 0.57),
#     "sweep": (2, 0.57),
#     "TossToyIntoBox": (1, 0.57),
#     "wipe_new": (1, 0.57),
#     "PourTrash": (1, 0.57),
#     "PrepareForSnack": (1, 0.57),
#     "PenHolder": (1, 0.57),
#     "candy": (0.1, 0.57),
#     "writing_desk_vp": (2, 0.57),
#     "writing_desk_scoop": (0.5, 0.57),
#     "writing_desk_penholder": (2, 0.57),
#     "writing_desk_bookwithbookend": (0.5, 0.57),
#     "dagger_book": (0.25, 0.57),
#     "dagger_pp": (0.5, 0.57),
#     "scoop_tea": (0.5, 0.57),
#     "AdjustBowlPosition": (1, 0.57),
#     "WipeSpillArea": (0.5, 0.57),
#     "PickStackedBowls": (0.2, 0.57),
#     "tie_knot": (1, 0.57),
#     "cocktail": (0.5, 0.57),
#     "basketball": (0.5, 0.57),
#     "twist_bottle_cap": (0.5, 0.57),
#     "SkewerFruits": (1, 0.57)
# }


## SkewerFruits v3

# GROUP_CONFIG = {
#     "SkewerFruits": (1, 0),
#     "writing_desk_vp": (1, 0.7),
#     "pick_place": (1, 0.7),
#     "writing_desk_scoop": (1, 0.7),
#     "writing_desk_penholder": (1, 0.7),
#     "writing_desk_bookwithbookend": (1, 0.7)
# }



# # # 0426 cotrain
# GROUP_CONFIG = {
#     "human_interaction": (1, 0.57),
#     "pick_place": (2, 0.57),
#     "drawer": (1, 0.57),
#     "insert": (2, 0.57),
#     "insert_dagger": (1, 0.57),
#     "makesandwich": (1, 0.57),
#     "stack": (1, 0.57),
#     "waterflowers": (1, 0.57),
#     "PourWater": (1, 0.57),
#     "sweep": (2, 0.57),
#     "TossToyIntoBox": (1, 0.57),
#     "wipe_new": (1, 0.57),
#     "PourTrash": (1, 0.57),
#     "PrepareForSnack": (1, 0.57),
#     "PenHolder": (1, 0.57),
#     "candy": (0.1, 0.57),
#     "writing_desk_vp": (8, 0.57),
#     "writing_desk_scoop": (0.25, 0.57),
#     "writing_desk_penholder": (2, 0.57),
#     "writing_desk_bookwithbookend": (0.25, 0.57),
#     "dagger_book": (0.25, 0.57),
#     "dagger_pp": (1, 0.57),
#     "scoop_tea": (0.5, 0.57),
#     "AdjustBowlPosition": (1, 0.57),
#     "WipeSpillArea": (0.5, 0.57),
#     "PickStackedBowls": (0.2, 0.57),
#     "tie_knot": (1, 0.57),
#     "cocktail": (0.5, 0.57),
#     "basketball": (0.5, 0.57),
#     "twist_bottle_cap": (0.5, 0.57),
#     "SkewerFruits": (1, 0.57)
# }


# 0428 no_reset 书桌demo - 提高插笔比例

GROUP_CONFIG = {
    "desk_penholder_rich": (2, 0.57),  # 插笔动作多（1086, 1384），权重 2
    "desk_pickplace": (1, 0.57),       # 普通 pick&place（1011, 1026），权重 1
}


# ============================================================================


def load_total_frames(dataset_paths: List[str], base_dir: Path) -> Dict[str, int]:
    """加载每个数据集的总帧数"""
    frames = {}
    for path in dataset_paths:
        info_path = base_dir / path / "meta" / "info.json"
        if not info_path.exists():
            raise FileNotFoundError(f"找不到 info.json: {info_path}")
        with open(info_path, 'r') as f:
            info = json.load(f)
        frames[path] = info['total_frames']
    return frames


def group_datasets(dataset_paths: List[str], group_rules: dict) -> Dict[str, List[str]]:
    """
    将数据集按规则分组

    Args:
        dataset_paths: 所有数据集路径
        group_rules: {组名: 关键词} 或 {组名: [关键词列表]}

    Returns:
        {组名: [数据集路径列表]} 映射，未匹配的数据集归入 "_other" 组
    """
    groups = {name: [] for name in group_rules}
    groups["_other"] = []

    for path in dataset_paths:
        matched = False
        for group_name, keywords in group_rules.items():
            # 支持单个关键词或关键词列表
            if isinstance(keywords, str):
                keywords = [keywords]
            if any(kw in path for kw in keywords):
                groups[group_name].append(path)
                matched = True
                break
        if not matched:
            groups["_other"].append(path)

    return groups


def parse_group_config(config: tuple) -> tuple:
    """
    解析组配置，返回 (比例值, alpha, is_fixed)

    支持格式：
    - (ratio, alpha) -> (ratio, alpha, False)
    - (ratio, alpha, is_fixed) -> (ratio, alpha, is_fixed)
    """
    if len(config) == 2:
        return (config[0], config[1], False)
    elif len(config) == 3:
        return (config[0], config[1], bool(config[2]))
    else:
        raise ValueError(f"组配置格式错误，期望 (ratio, alpha) 或 (ratio, alpha, is_fixed)，得到: {config}")


def compute_sampling_weights(
    frames: Dict[str, int],
    groups: Dict[str, List[str]],
    group_config: Dict[str, tuple]
) -> Dict[str, float]:
    """
    计算调整后的采样权重

    Args:
        frames: {数据集路径: 帧数}
        groups: {组名: [数据集路径列表]}
        group_config: {组名: (比例值, power_alpha) 或 (比例值, power_alpha, is_fixed)}

    Returns:
        {数据集路径: 采样权重}
    """
    # 验证：所有有数据集的组（除了 _other）都必须在 group_config 中配置
    for group_name, datasets in groups.items():
        if group_name == "_other":
            continue
        if datasets and group_name not in group_config:
            raise ValueError(f"组 [{group_name}] 有 {len(datasets)} 个数据集，但未在 GROUP_CONFIG 中配置比例")

    # 解析配置：分离固定占比组和相对数值组
    fixed_groups = {}      # {组名: 固定占比}
    relative_groups = {}   # {组名: 相对数值}
    group_alphas = {}      # {组名: alpha}

    for group_name, config in group_config.items():
        ratio, alpha, is_fixed = parse_group_config(config)
        group_alphas[group_name] = alpha
        if is_fixed:
            fixed_groups[group_name] = ratio
        else:
            relative_groups[group_name] = ratio

    # 验证固定占比之和不超过 1.0
    fixed_sum = sum(fixed_groups.values())
    if fixed_sum > 1.0 + 1e-9:
        raise ValueError(f"固定占比之和超过 1.0: {fixed_sum:.4f}")
    if fixed_sum < 0:
        raise ValueError(f"固定占比之和不能为负: {fixed_sum}")

    # 计算相对组可分配的剩余比例
    remaining_ratio = 1.0 - fixed_sum

    # 对相对数值组进行归一化，分配剩余比例
    relative_sum = sum(relative_groups.values())
    if relative_groups and relative_sum <= 0:
        raise ValueError(f"相对数值组的比例值之和必须大于0，当前为: {relative_sum}")

    # 计算最终的归一化比例
    normalized_ratios = {}
    for group_name, ratio in fixed_groups.items():
        normalized_ratios[group_name] = ratio
    for group_name, ratio in relative_groups.items():
        normalized_ratios[group_name] = (ratio / relative_sum) * remaining_ratio if relative_sum > 0 else 0

    # _other 组不参与采样
    all_ratios = {**normalized_ratios, "_other": 0.0}
    all_alphas = {**group_alphas, "_other": 1.0}  # _other 组默认均匀采样

    # 计算每个数据集的目标 frame 采样比例
    target_probs = {}
    for group_name, datasets in groups.items():
        if not datasets:
            continue
        group_ratio = all_ratios.get(group_name, 0)
        if group_ratio == 0:
            # _other 组或显式配置比例为 0 的组不参与采样
            continue

        alpha = all_alphas.get(group_name, 1.0)

        # Power law 分配：组内每个数据集的 frame 采样比例 ∝ frames^(1-alpha)
        # alpha=1: 均匀采样（每个数据集比例相同）
        # alpha=0: 按帧数比例采样
        ds_frames = [frames[ds] for ds in datasets]
        ds_powers = [f ** (1 - alpha) for f in ds_frames]
        total_power = sum(ds_powers)

        for ds, power in zip(datasets, ds_powers):
            target_probs[ds] = group_ratio * (power / total_power)

    # 计算采样权重: w_i = target_prob_i / frames_i
    weights = {}
    for ds, prob in target_probs.items():
        weights[ds] = prob / frames[ds]

    # 归一化：让最小权重 >= 0.01
    if weights:
        min_weight = min(weights.values())
        if min_weight > 0 and min_weight < 0.01:
            import math
            # 计算需要乘的 10^n，使最小值 >= 0.01
            n = math.ceil(-2 - math.log10(min_weight))
            scale = 10 ** n
            weights = {k: v * scale for k, v in weights.items()}

    return weights


def analyze_sampling(
    weights: Dict[str, float],
    frames: Dict[str, int],
    groups: Dict[str, List[str]]
) -> None:
    """打印采样分析结果"""
    # 计算实际的 frame 采样比例
    total = sum(frames[ds] * w for ds, w in weights.items())

    print("\n" + "="*80)
    print("采样分析结果")
    print("="*80)

    for group_name, datasets in groups.items():
        if not datasets:
            continue

        # 检查该组是否有数据集参与采样
        included = [ds for ds in datasets if ds in weights]
        excluded = [ds for ds in datasets if ds not in weights]

        if included:
            print(f"\n【{group_name}】({len(included)} 个数据集)")
            group_frame_ratio = 0
            for ds in included:
                w = weights[ds]
                f = frames[ds]
                frame_ratio = (f * w) / total
                group_frame_ratio += frame_ratio
                print(f"  {ds}")
                print(f"    帧数: {f:,}, 权重: {w:.6e}, Frame采样比: {frame_ratio:.4%}")
            print(f"  ➜ 组总Frame采样比: {group_frame_ratio:.4%}")

        if excluded:
            print(f"\n【{group_name}（未采样）】({len(excluded)} 个数据集)")
            for ds in excluded:
                print(f"  {ds} (占比为0，不参与采样)")

    print("\n" + "="*80)


def adjust_sampling_ratio(
    input_json: str,
    group_rules: dict,
    group_config: Dict[str, tuple],
    base_dir: str = None,
    output_json: str = None,
    verbose: bool = True
) -> Dict[str, float]:
    """
    调整数据集采样比例

    Args:
        input_json: 输入的JSON文件路径
        group_rules: {组名: 关键词} 或 {组名: [关键词列表]}
        group_config: {组名: (目标占比, power_alpha)}
        base_dir: 数据集根目录，默认为input_json所在目录
        output_json: 输出JSON文件路径，默认为None（不保存）
        verbose: 是否打印详细信息

    Returns:
        调整后的采样权重字典
    """
    input_path = Path(input_json)
    base_path = Path(base_dir) if base_dir else input_path.parent

    # 加载原始 JSON
    with open(input_path, 'r') as f:
        original = json.load(f)

    dataset_paths = list(original.keys())

    # 加载帧数
    if verbose:
        print(f"加载 {len(dataset_paths)} 个数据集的帧数...")
    frames = load_total_frames(dataset_paths, base_path)

    # 分组
    groups = group_datasets(dataset_paths, group_rules)

    # 解析配置并计算归一化后的比例（用于显示）
    fixed_groups = {}
    relative_groups = {}
    group_alphas_display = {}

    for name, config in group_config.items():
        ratio, alpha, is_fixed = parse_group_config(config)
        group_alphas_display[name] = alpha
        if is_fixed:
            fixed_groups[name] = ratio
        else:
            relative_groups[name] = ratio

    fixed_sum = sum(fixed_groups.values())
    remaining_ratio = 1.0 - fixed_sum
    relative_sum = sum(relative_groups.values())

    if verbose:
        print(f"\n  固定占比组总计: {fixed_sum:.2%}, 相对组可分配比例: {remaining_ratio:.2%}")
        for name, datasets in groups.items():
            if name in fixed_groups:
                ratio = fixed_groups[name]
                alpha = group_alphas_display[name]
                print(f"  组 [{name}]: {len(datasets)} 个数据集, 固定占比={ratio:.2%}, α={alpha}")
            elif name in relative_groups:
                raw_ratio = relative_groups[name]
                norm_ratio = (raw_ratio / relative_sum) * remaining_ratio if relative_sum > 0 else 0
                alpha = group_alphas_display[name]
                print(f"  组 [{name}]: {len(datasets)} 个数据集, 相对值={raw_ratio:.4f}, 归一化占比={norm_ratio:.2%}, α={alpha}")
            elif name == "_other" and datasets:
                print(f"  组 [{name}]: {len(datasets)} 个数据集 (不参与采样)")

    # 计算新权重
    weights = compute_sampling_weights(frames, groups, group_config)

    # 分析结果
    if verbose:
        analyze_sampling(weights, frames, groups)

    # 保存结果
    if output_json:
        with open(output_json, 'w') as f:
            json.dump(weights, f, indent=2)
        if verbose:
            print(f"\n结果已保存到: {output_json}")

    return weights


def main():
    """使用文件中定义的配置运行"""
    adjust_sampling_ratio(
        input_json=INPUT_JSON,
        group_rules=GROUP_RULES,
        group_config=GROUP_CONFIG,
        output_json=OUTPUT_JSON
    )


if __name__ == "__main__":
    main()