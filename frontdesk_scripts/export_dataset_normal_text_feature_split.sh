#!/bin/bash

# 使用关联数组定义任务配置（bash 4.0+）

# 定义每个任务ID对应的文件名
declare -A FILE_NAME_MAP
# FILE_NAME_MAP["535"]="20251021_pickplacevp1022_pickshelf_lrm_hrpi2_yhvp_1"
# FILE_NAME_MAP["536"]="20251021_pickplacevp1022_placeshelf_lmr_hrpi2_yhvp_2"
# FILE_NAME_MAP["537"]="20251021_pickplacevp1022_placeanywheredesk_lrbt_hrpi2_yhvp_3"
# FILE_NAME_MAP["578"]="20251031_1106basedata_laystand_moz1"
# FILE_NAME_MAP["564"]="20251030_1106basedata_laystand_moz1"
# FILE_NAME_MAP["562"]="20251029_1106basedata_laystand_moz1"
# FILE_NAME_MAP["561"]="20251028_1106basedata_laystand_moz1"
# FILE_NAME_MAP["547"]="20251023_pushpulldrawer_moz1"
# FILE_NAME_MAP["517"]="20251019_pickplacevp1020_picktable_lrfb_hrpi2_yhvp_1"
# # FILE_NAME_MAP["518"]="20251019_pickplacevp1020_picktable_rc_hrpi2_yhvp_2"
# FILE_NAME_MAP["519"]="20251019_pickplacevp1020_pickshelf_lrm_hrpi2_yhvp_3"
# FILE_NAME_MAP["520"]="20251019_pickplacevp1020_pickegg_singlecr_hrpi2_yhvp_4"
# FILE_NAME_MAP["521"]="20251019_pickplacevp1020_pickegg_doublecr_hrpi2_yhvp_5"
# FILE_NAME_MAP["522"]="20251019_pickplacevp1020_placeegg_singlecr_hrpi2_yhvp_6"
# FILE_NAME_MAP["523"]="20251019_pickplacevp1020_placeegg_doublecr_hrpi2_yhvp_7"
# FILE_NAME_MAP["524"]="20251019_pickplacevp1020_placedrawer_singleumr_hrpi2_yhvp_8"
# # FILE_NAME_MAP["525"]="20251019_pickplacevp1020_placedrawer_doubleumr_hrpi2_yhvp_9"
# FILE_NAME_MAP["526"]="20251019_pickplacevp1020_placecupshelf_singlecr_hrpi2_yhvp_10"
# FILE_NAME_MAP["527"]="20251019_pickplacevp1020_placecupshelf_doublecr_hrpi2_yhvp_11"
# FILE_NAME_MAP["528"]="20251019_pickplacevp1020_placealloc_double_hrpi2_yhvp_12"
# FILE_NAME_MAP["529"]="20251019_pickplacevp1020_placeshelf_mn_hrpi2_yhvp_13"
# FILE_NAME_MAP["530"]="20251019_pickplacevp1020_placeplate_mn_hrpi2_yhvp_14"
# FILE_NAME_MAP["531"]="20251019_pickplacevp1020_placemul_lrtb_hrpi2_yhvp_15"
# FILE_NAME_MAP["630"]="20251109_office_water_triangle_moz1_yh_v2"
# FILE_NAME_MAP["707"]="20251117_force_cftest_mozWB"
# FILE_NAME_MAP["695"]="20251116_demodailytrain_office_watertriangle_moz1WB"
# FILE_NAME_MAP["693"]="20251116_demodailytrain_office_pickwater_moz1WB"
# FILE_NAME_MAP["689"]="20251115_demodailytrain_office_pickwater_moz1WB"
# FILE_NAME_MAP["680"]="20251114_demodailytrain_office_pickwater_moz1WB"


# FILE_NAME_MAP["715"]="20251118_FrontDeskDemo_WBWB_tissuwipethrow"
# FILE_NAME_MAP["722"]="20251119_FrontDeskDemo_WBWB_tissuwipethrow"

# FILE_NAME_MAP["744"]="20251120_liftwater_1_forcecontrol_17_new"

# FILE_NAME_MAP["741"]="20251120_FrontDeskDemo_WBWB_insertflower"

# FILE_NAME_MAP["740"]="20251119_FrontDeskDemo_WBWB_WaterFlowers_V1"
# FILE_NAME_MAP["735"]="20251120_FrontDeskDemo_WBWB_Humaninteraction"
# FILE_NAME_MAP["733"]="20251120_FrontDeskDemo_WBWB_sweep_y06"
# FILE_NAME_MAP["725"]="20251119_FrontDeskDemo_WBWB_drawer"
# FILE_NAME_MAP["724"]="20251119_FrontDeskDemo_WBWB_StackDish"

# FILE_NAME_MAP["768"]="20251123_FrontDeskDemo_WBWB_WaterFlowers_V1"
# FILE_NAME_MAP["767"]="20251123_FrontDeskDemo_WBWB_Humaninteraction"
# FILE_NAME_MAP["766"]="20251122_FrontDeskDemo_WBWB_insertflower"
# FILE_NAME_MAP["762"]="20251123_FrontDeskDemo_WBWB_ShakeNWave"
# FILE_NAME_MAP["761"]="20251122_FrontDeskDemo_WBWB_drawer"
# FILE_NAME_MAP["760"]="20251122_FrontDeskDemo_WBWB_WaterFlowers_V1"
# FILE_NAME_MAP["759"]="20251122_FrontDeskDemo_WBWB_Humaninteraction"
# FILE_NAME_MAP["756"]="20251122_FrontDeskDemo_PlugInNOut_V1_WBWB"
# FILE_NAME_MAP["755"]="20251122_FrontDeskDemo_WBWB_ShakeNWave"
# FILE_NAME_MAP["750"]="20251121_FrontDeskDemo_WBWB_sweep"
# FILE_NAME_MAP["748"]="20251123_FrontDeskDemo_WBWB_FoldHoody"
# FILE_NAME_MAP["747"]="20251121_FrontDeskDemo_WBWB_ShakeNWave"
# FILE_NAME_MAP["745"]="20251121_FrontDeskDemo_WBWB_WaterFlowers_V1"
# FILE_NAME_MAP["742"]="20251121_FrontDeskDemo_PlugInNOut_V1_WBWB"


# FILE_NAME_MAP["795"]="20251126_FrontDeskDemo_PlugInNOut_V1_WBWB_better"
# FILE_NAME_MAP["794"]="20251126_FrontDeskDemo_WBWB_WaterFlowers_V1_better"
# FILE_NAME_MAP["793"]="20251126_FrontDeskDemo_WBWB_sweep_better"

# FILE_NAME_MAP["787"]="20251125_FrontDeskDemo_WBWB_ShakeNWave"
# FILE_NAME_MAP["786"]="20251125_FrontDeskDemo_WBWB_Humaninteraction"
# FILE_NAME_MAP["785"]="20251125_FrontDeskDemo_WBWB_insertflower"
# FILE_NAME_MAP["784"]="20251125_FrontDeskDemo_WBWB_FoldHoody"
# FILE_NAME_MAP["774"]="20251124_FrontDeskDemo_WBWB_FoldHoody"
# FILE_NAME_MAP["773"]="20251124_FrontDeskDemo_WBWB_insertflower"
# FILE_NAME_MAP["772"]="20251124_FrontDeskDemo_WBWB_Humaninteraction"
# FILE_NAME_MAP["771"]="20251124_FrontDeskDemo_WBWB_ShakeNWave"


# FILE_NAME_MAP["803"]="20251128_FrontDeskDemo_WBWB_Insert_V2"
# FILE_NAME_MAP["802"]="20251126_FrontDeskDemo_WBWB_PourWater_V2"
# FILE_NAME_MAP["801"]="20251128_FrontDeskDemo_WBWB_sweep_v2"
# FILE_NAME_MAP["779"]="20251124_PlaceTableware_FrontDeskDemo_WB"
# FILE_NAME_MAP["780"]="20251124_PlaceFlatware_FrontDeskDemo_WB"

# FILE_NAME_MAP["835"]="20251204_TossToyIntoBox_Toss_Moz1WB"
# FILE_NAME_MAP["850"]="20251208_NoReset_StackBowl_Stack_FrontDeskDemo_Moz1WB"

# FILE_NAME_MAP["851"]="20251208_NoReset_VisualPrompt_PickPlace_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["796"]="20251126_FrontDeskDemo_WBWB_Microwave_button_better"
# FILE_NAME_MAP["869"]="20251209_NoReset_StackBowl_Stack_FrontDeskDemo_Moz1WB"

# FILE_NAME_MAP["877"]="20251210_PourWater_v3_Pour_FrontDeskDemo_Moz1WB"

# FILE_NAME_MAP["875"]="20251210_sweep_v3_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["876"]="20251210_WaterFlower_v3_Pour_FrontDeskDemo_Moz1WB"

# FILE_NAME_MAP["1000"]="20251225_Pick&PlaceEverything_Visual_Prompt_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1011"]="20251228_Pick&PlaceEverything_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1014"]="20251228_ScoopNuts_WritingDesk_FrontDeskDemo_Moz1WB_0105_pull"
# FILE_NAME_MAP["1015"]="20251228_PenHolder_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1026"]="20251230_PickPlaceEverythingWithBookshelf_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1028"]="20251231_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"

# FILE_NAME_MAP["1076"]="20260109_ScoopNutsHuman_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1077"]="20260109_ScoopNuts_WritingDesk_FrontDeskDemo_Moz1WB"



# FILE_NAME_MAP["823"]="20251119_FrontDeskDemo_WBWB_Wipe_VisualPrompt"
# FILE_NAME_MAP["824"]="20251202_FrontDeskDemo_WBWB_pickplace_VisualPrompt"

# FILE_NAME_MAP["1090"]="20260112_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1091"]="20260112_AdjustBowlPosition_WritingDesk_FrontDeskDemo"
# FILE_NAME_MAP["1098"]="20260112_WipeSpillArea_WritingDesk_FrontDeskDemo"
# FILE_NAME_MAP["1099"]="20260112_PickStackedBowls_WritingDesk_FrontDeskDemo"


# FILE_NAME_MAP["888"]="20251212_Wipe_VisualPrompt_FrontDeskDemo_WBWB"
# FILE_NAME_MAP["889"]="20251212_PourTrash_v3_Pour_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["890"]="20251212_Book_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["896"]="20251216_WaterDispenser_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["897"]="20251216_ScoopTea_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["941"]="20251218_PrepareForSnack_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["942"]="20251218_PenHolder_FrontDeskDemo_Moz1WB "
# FILE_NAME_MAP["951"]="20251218_FrontDeskDemo_WBWB_insertflower_v3"
# FILE_NAME_MAP["999"]="20251225_Book_VisualPrompt_NewWritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1012"]="20251228_Book_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1086"]="20260109_PickPlaceEverythingWithBookshelf_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1088"]="20260110_ObstacleAvoidingPickPlaceEverythingWithBookshelf_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB_V2"
# FILE_NAME_MAP["1135"]="20260113_PickPlaceEverythingWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB"


# FILE_NAME_MAP["999"]="20251225_Book_VisualPrompt_NewWritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1000"]="20251225_Pick&PlaceEverything_Visual_Prompt_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1011"]="20251228_Pick&PlaceEverything_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1012"]="20251228_Book_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1014"]="20251228_ScoopNuts_WritingDesk_FrontDeskDemo_Moz1WB_0105_pull"
# FILE_NAME_MAP["1015"]="20251228_PenHolder_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1026"]="20251230_PickPlaceEverythingWithBookshelf_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1028"]="20251231_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1076"]="20260109_ScoopNutsHuman_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1077"]="20260109_ScoopNuts_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1086"]="20260109_PickPlaceEverythingWithBookshelf_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1088"]="20260110_ObstacleAvoidingPickPlaceEverythingWithBookshelf_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB_V2"
# FILE_NAME_MAP["1090"]="20260112_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1091"]="20260112_AdjustBowlPosition_WritingDesk_FrontDeskDemo"
# FILE_NAME_MAP["1098"]="20260112_WipeSpillArea_WritingDesk_FrontDeskDemo"
# FILE_NAME_MAP["1099"]="20260112_PickStackedBowls_WritingDesk_FrontDeskDemo"
# FILE_NAME_MAP["1135"]="20260113_PickPlaceEverythingWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1138"]="20260113_WipeSpillArea_WritingDesk_FrontDeskDemo"
# FILE_NAME_MAP["1151"]="20260115_TieKnot__Moz1WB"
# FILE_NAME_MAP["1165"]="20260116_DrawerOpened_PickPlaceEverythingWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1166"]="20260116_DrawerOpened_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1168"]="20260116_DrawerOpened_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB"


# FILE_NAME_MAP["999"]="20251225_Book_VisualPrompt_NewWritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1012"]="20251228_Book_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1028"]="20251231_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1146"]="20260114_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1166"]="20260116_DrawerOpened_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1186"]="20260119_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1215"]="20260122_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"


# FILE_NAME_MAP["1274"]="20260126_MakeOden_CCTVDemo_Moz1WB"


# FILE_NAME_MAP["825"]="20251202_FrontDeskDemo_WBWB_Insert_dagger"
# FILE_NAME_MAP["949"]="20251219_norollback_FrontDeskDemo_WBWB_Insertflower_dagger"
# FILE_NAME_MAP["950"]="20251219_rollback_FrontDeskDemo_WBWB_Insertflower_dagger"
# FILE_NAME_MAP["961"]="20251219_CocktailUmbrella_PromptReseach_Demo_Moz1WB"
# FILE_NAME_MAP["959"]="20251219_CupName_PromptReseach_Demo_Moz1WB"
# FILE_NAME_MAP["1001"]="20251225_CocktailUmbrella_PromptReseach_Demo_Moz1WB"
# FILE_NAME_MAP["1051"]="20260105_basketball_Moz1WB"
# FILE_NAME_MAP["1079"]="20260105_basketball_once_Moz1WB"
# FILE_NAME_MAP["1118"]="20260105_basketball_OnceBetter_Moz1WB"


# FILE_NAME_MAP["1135"]="20260113_PickPlaceEverythingWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1138"]="20260113_WipeSpillArea_WritingDesk_FrontDeskDemo"
# FILE_NAME_MAP["1146"]="20260114_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1165"]="20260116_DrawerOpened_PickPlaceEverythingWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1169"]="20260115_writingdesk_v1_putback_book_WBWB_dagger"
# FILE_NAME_MAP["1170"]="20260115_writingdesk_v1_takebook_WBWB_dagger"
# FILE_NAME_MAP["1186"]="20260119_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1188"]="20260119_PickPlaceBookWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1215"]="20260122_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1225"]="20260122_TwistBottleCap_Moz1WB"
# FILE_NAME_MAP["1239"]="20260125_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1244"]="20260126_Bookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1275"]="20260127_PenHolder_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1276"]="20260127_BowlScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1277"]="20260127_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1293"]="20260128_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1294"]="20260128_BowlScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB"

# FILE_NAME_MAP["1332"]="20260130_MakeOden_CCTVDemo_Moz1WB"
# FILE_NAME_MAP["1362"]="20260131_MakeOden_CCTVDemo_Moz1WB"

# FILE_NAME_MAP["1324"]="20260129_PickPlaceEverythingWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB"


# FILE_NAME_MAP["1225"]="20260122_TwistBottleCap_DataLoop_FrontDeskDemo_Moz1WB"


# FILE_NAME_MAP["1381"]="20260202_SkewerFruits_ExhibitionDemo_Moz1WB"


# FILE_NAME_MAP["1383"]="20260203_DrawerOpenedPickPlaceEverythingWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1384"]="20260203_MoveObjectWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1387"]="20260203_ObstacleAvoidingPickPlaceEverythingWithBookshelf_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB_V2"
# FILE_NAME_MAP["1440"]="20260206_MovePen_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1413"]="20260205_DrawerOpenedPickPlaceEverythingWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB"


# FILE_NAME_MAP["1497"]="20260209_SkewerFruits_V2_ExhibitionDemo_Moz1WB"



# FILE_NAME_MAP["1562"]="20260225_SkewerFruits_V3_ExhibitionDemo_Moz1WB"
# FILE_NAME_MAP["1581"]="20260226_SkewerFruits_SupplementData_V3_ExhibitionDemo_Moz1WB"
# FILE_NAME_MAP["1768"]="20260303_SkewerFruits_TakeCup_V3_ExhibitionDemo_Moz1WB"


# FILE_NAME_MAP["1769"]="20260303_SkewerFruits_FullProcess_V3_ExhibitionDemo_Moz1WB"
# FILE_NAME_MAP["1923"]="20250306_CupUpright_DataLoop_FrontDeskDemo_Moz1WB"




# FILE_NAME_MAP["2291"]="20260313_SkewerFruits_FullProcess_V4_ExhibitionDemo_Moz1WB"
# FILE_NAME_MAP["2292"]="20260313_SkewerFruits_one_V4_ExhibitionDemo_Moz1WB"


# FILE_NAME_MAP["2379"]="20260315_SkewerFruits_FullProcess_V4_ExhibitionDemo_Moz1WB"

# FILE_NAME_MAP["2817"]="20260322_SkewerFruits_Step1and2_V4_ExhibitionDemo_Moz1WB"
# FILE_NAME_MAP["2824"]="20260326_SkewerFruits_one_V4_ExhibitionDemo_Moz1WB"


# FILE_NAME_MAP["4122"]="20260410_SkewerFruits_V5_ExhibitionDemo_Moz1WB"
# FILE_NAME_MAP["4123"]="20260411_SkewerFruits_PlacePlate_V5_ExhibitionDemo_Moz1WB"
# FILE_NAME_MAP["4243"]="20260411_SkewerFruits_step2_V5_ExhibitionDemo_Moz1WB"


# FILE_NAME_MAP["4506"]="20260414_SkewerFruits_step2_V5_ExhibitionDemo_Moz1WB"

# FILE_NAME_MAP["3452"]="20260401_CapsuleToy_Moz1"
# FILE_NAME_MAP["4146"]="20260410_CapsuleToy_Interaction_Moz1"
# FILE_NAME_MAP["5485"]="20260427_CapsuleToy_Enhanced_Moz1"



# FILE_NAME_MAP["1384"]="20260203_MoveObjectWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1086"]="20260109_PickPlaceEverythingWithBookshelf_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1026"]="20251230_PickPlaceEverythingWithBookshelf_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["1011"]="20251228_Pick&PlaceEverything_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["851"]="20251208_NoReset_VisualPrompt_PickPlace_FrontDeskDemo_Moz1WB"








# FILE_NAME_MAP["2050"]="20260309_HouseholdDemo_WipeTable_atDemoRegion_UDAS_raw"
# FILE_NAME_MAP["2432"]="20260316_HouseholdDemo_WipeTable_UDAS_raw_better"
# FILE_NAME_MAP["2547"]="20260317_HouseholdDemo_WipeTable_UDAS_raw_better_V2"
# FILE_NAME_MAP["2548"]="20260318_HouseholdDemo_WipeTable_atDemoRegion_UDAS_raw"

# FILE_NAME_MAP["2871"]="20260323_HouseholdDemo_CollectTrash_DemoRegion_teleop"


# FILE_NAME_MAP["2162"]="20260311_HouseholdDemo_WipeTable_teleop"

# FILE_NAME_MAP["2548"]="20260318_HouseholdDemo_WipeTable_atDemoRegion_UDAS_raw"
# FILE_NAME_MAP["2432"]="20260316_HouseholdDemo_WipeTable_UDAS_raw_better"
# FILE_NAME_MAP["2050"]="20260309_HouseholdDemo_WipeTable_atDemoRegion_UDAS_raw"


# FILE_NAME_MAP["2378"]="20260315_CollectTrash_HouseholdDemo_UDAS_raw_better"
# FILE_NAME_MAP["2552"]="20260318_HouseholdDemo_CollectTrash_teleop"

# FILE_NAME_MAP["2432"]="20260316_HouseholdDemo_WipeTable_UDAS_raw_better"
# FILE_NAME_MAP["2547"]="20260317_HouseholdDemo_WipeTable_UDAS_raw_better_V2"

# FILE_NAME_MAP["2050"]="20260309_HouseholdDemo_WipeTable_atDemoRegion_UDAS_raw"
# FILE_NAME_MAP["2548"]="20260318_HouseholdDemo_WipeTable_atDemoRegion_UDAS_raw"




# FILE_NAME_MAP["2162"]="20260311_HouseholdDemo_WipeTable_teleop"
# FILE_NAME_MAP["2553"]="20260318_HouseholdDemo_WipeTable_atDemoRegion_teleop"


# FILE_NAME_MAP["441"]="20250924_pick_place_moz1"


# FILE_NAME_MAP["2801"]="20260321_SkewerFruits_Step1and2_V4_ExhibitionDemo_Moz1WB"

# FILE_NAME_MAP["5050"]="20260420_SortPills_NarrowTable_FrontDeskDemo_Moz1WB"

# FILE_NAME_MAP["6038"]="20260501_SortPills_V2_NarrowTable_FrontDeskDemo_Udas"
#FILE_NAME_MAP["6037"]="20260501_SortPills_V2_NarrowTable_FrontDeskDemo_Moz1WB"
#FILE_NAME_MAP["6255"]="20260507_SortPills_V2_NarrowTable_FrontDeskDemo_NewGripper"
#FILE_NAME_MAP["6538"]="20260509_SortPills_V2_NarrowTable_FrontDeskDemo_Udas"
# FILE_NAME_MAP["6667"]="20260511_SortPills_V2_NarrowTable_FrontDeskDemo_Moz1WB"
# FILE_NAME_MAP["2378"]="20260315_CollectTrash_HouseholdDemo_UDAS_raw_better"

# FILE_NAME_MAP["7067"]="20260515_SortPills_V2_NarrowTable_FrontDeskDemo_NewGripper"

# FILE_NAME_MAP["7184"]="20260515_PickupPencil_Conveyor"
# FILE_NAME_MAP["7067"]="20260515_SortPills_V2_NarrowTable_FrontDeskDemo_NewGripper"
# FILE_NAME_MAP["7184"]="20260515_PickupPencil_Conveyor"
# FILE_NAME_MAP["8303"]="20260521_Unlock_NarrowTable_Moz1WB"


FILE_NAME_MAP["8571"]="旧感知插花插笔20260525_pi05_old_Flower_Pen_Demo_24_30000"











# 定义每个任务ID对应的子目录（可选，如果某个ID没有定义，会使用默认值从文件名提取）
declare -A SUBDIR_MAP
# SUBDIR_MAP["716"]="StackDish/normal"
# SUBDIR_MAP["768"]="v2_FrontDeskDemo"
# SUBDIR_MAP["767"]="v2_FrontDeskDemo"
# SUBDIR_MAP["766"]="v2_FrontDeskDemo"
# SUBDIR_MAP["762"]="v2_FrontDeskDemo"
# SUBDIR_MAP["761"]="v2_FrontDeskDemo"
# SUBDIR_MAP["760"]="v2_FrontDeskDemo"
# SUBDIR_MAP["759"]="v2_FrontDeskDemo"
# SUBDIR_MAP["756"]="v2_FrontDeskDemo"
# SUBDIR_MAP["755"]="v2_FrontDeskDemo"
# SUBDIR_MAP["750"]="v2_FrontDeskDemo"
# SUBDIR_MAP["748"]="v2_FrontDeskDemo"
# SUBDIR_MAP["747"]="v2_FrontDeskDemo"
# SUBDIR_MAP["745"]="v2_FrontDeskDemo"
# SUBDIR_MAP["742"]="v2_FrontDeskDemo"


# SUBDIR_MAP["795"]="v4_FrontDeskDemo"
# SUBDIR_MAP["794"]="v4_FrontDeskDemo"
# SUBDIR_MAP["793"]="v4_FrontDeskDemo"

# SUBDIR_MAP["787"]="v3_FrontDeskDemo"
# SUBDIR_MAP["786"]="v3_FrontDeskDemo"
# SUBDIR_MAP["785"]="v3_FrontDeskDemo"
# SUBDIR_MAP["784"]="v3_FrontDeskDemo"
# SUBDIR_MAP["774"]="v3_FrontDeskDemo"
# SUBDIR_MAP["773"]="v3_FrontDeskDemo"
# SUBDIR_MAP["772"]="v3_FrontDeskDemo"
# SUBDIR_MAP["771"]="v3_FrontDeskDemo"

# SUBDIR_MAP["803"]="v5_FrontDeskDemo"
# SUBDIR_MAP["802"]="v5_FrontDeskDemo"
# SUBDIR_MAP["801"]="v5_FrontDeskDemo"
# SUBDIR_MAP["779"]="v5_FrontDeskDemo"
# SUBDIR_MAP["780"]="v5_FrontDeskDemo"
# SUBDIR_MAP["835"]="v6_FrontDeskDemo_test"
# SUBDIR_MAP["850"]="v5_5_FrontDeskDemo"

# SUBDIR_MAP["851"]="v6_FrontDeskDemo"
# SUBDIR_MAP["796"]="v6_FrontDeskDemo"
# SUBDIR_MAP["869"]="v6_FrontDeskDemo"

# SUBDIR_MAP["877"]="v6_FrontDeskDemo_test"

# SUBDIR_MAP["875"]="v6_FrontDeskDemo_test"
# SUBDIR_MAP["876"]="v6_FrontDeskDemo_test"


# SUBDIR_MAP["1000"]="writingdesk"
# SUBDIR_MAP["1011"]="writingdesk"
# SUBDIR_MAP["1014"]="writingdesk"
# SUBDIR_MAP["1015"]="writingdesk"
# SUBDIR_MAP["1026"]="writingdesk"
# SUBDIR_MAP["1028"]="writingdesk"

# SUBDIR_MAP["1076"]="writingdesk"
# SUBDIR_MAP["1077"]="writingdesk"

# SUBDIR_MAP["823"]="wipe_new"
# SUBDIR_MAP["824"]="WB_pp_reset"

# SUBDIR_MAP["1090"]="writingdesk"
# SUBDIR_MAP["1091"]="writingdesk"
# SUBDIR_MAP["1098"]="writingdesk"
# SUBDIR_MAP["1099"]="writingdesk"

# SUBDIR_MAP["888"]="v7_FrontDeskDemo"
# SUBDIR_MAP["889"]="v7_FrontDeskDemo"
# SUBDIR_MAP["890"]="v7_FrontDeskDemo"
# SUBDIR_MAP["896"]="v7_FrontDeskDemo"
# SUBDIR_MAP["897"]="v7_FrontDeskDemo"
# SUBDIR_MAP["941"]="v7_FrontDeskDemo"
# SUBDIR_MAP["942"]="v7_FrontDeskDemo"
# SUBDIR_MAP["951"]="v7_FrontDeskDemo"
# SUBDIR_MAP["999"]="v7_FrontDeskDemo"
# SUBDIR_MAP["1012"]="v7_FrontDeskDemo"
# SUBDIR_MAP["1086"]="v7_FrontDeskDemo"
# SUBDIR_MAP["1088"]="v7_FrontDeskDemo"
# SUBDIR_MAP["1135"]="v7_FrontDeskDemo"


# SUBDIR_MAP["999"]="writingdesk_0117"
# SUBDIR_MAP["1000"]="writingdesk_0117"
# SUBDIR_MAP["1011"]="writingdesk_0117"
# SUBDIR_MAP["1012"]="writingdesk_0117"
# SUBDIR_MAP["1014"]="writingdesk_0117"
# SUBDIR_MAP["1015"]="writingdesk_0117"
# SUBDIR_MAP["1026"]="writingdesk_0117"
# SUBDIR_MAP["1028"]="writingdesk_0117"
# SUBDIR_MAP["1076"]="writingdesk_0117"
# SUBDIR_MAP["1077"]="writingdesk_0117"
# SUBDIR_MAP["1086"]="writingdesk_0117"
# SUBDIR_MAP["1088"]="writingdesk_0117"
# SUBDIR_MAP["1090"]="writingdesk_0117"
# SUBDIR_MAP["1091"]="writingdesk_0117"
# SUBDIR_MAP["1098"]="writingdesk_0117"
# SUBDIR_MAP["1099"]="writingdesk_0117"
# SUBDIR_MAP["1135"]="writingdesk_0117"
# SUBDIR_MAP["1138"]="writingdesk_0117"
# SUBDIR_MAP["1151"]="writingdesk_0117"
# SUBDIR_MAP["1165"]="writingdesk_0117"
# SUBDIR_MAP["1166"]="writingdesk_0117"
# SUBDIR_MAP["1168"]="writingdesk_0117"



# SUBDIR_MAP["999"]="writingdesk_0125"
# SUBDIR_MAP["1012"]="writingdesk_0125"
# SUBDIR_MAP["1028"]="writingdesk_0125"
# SUBDIR_MAP["1146"]="writingdesk_0125"
# SUBDIR_MAP["1166"]="writingdesk_0125"
# SUBDIR_MAP["1186"]="writingdesk_0125"
# SUBDIR_MAP["1215"]="writingdesk_0125"




# SUBDIR_MAP["1239"]="writingdesk_0126"


# SUBDIR_MAP["1274"]="cctv"


# SUBDIR_MAP["825"]="writingdesk_0130"
# SUBDIR_MAP["949"]="writingdesk_0130"
# SUBDIR_MAP["950"]="writingdesk_0130"
# SUBDIR_MAP["961"]="writingdesk_0130"
# SUBDIR_MAP["959"]="writingdesk_0130"
# SUBDIR_MAP["1001"]="writingdesk_0130"
# SUBDIR_MAP["1051"]="writingdesk_0130"
# SUBDIR_MAP["1079"]="writingdesk_0130"
# SUBDIR_MAP["1118"]="writingdesk_0130"



# SUBDIR_MAP["1135"]="writingdesk_0130"
# SUBDIR_MAP["1138"]="writingdesk_0130"
# SUBDIR_MAP["1146"]="writingdesk_0130"
# SUBDIR_MAP["1165"]="writingdesk_0130"
# SUBDIR_MAP["1169"]="writingdesk_0130"
# SUBDIR_MAP["1170"]="writingdesk_0130"
# SUBDIR_MAP["1186"]="writingdesk_0130"
# SUBDIR_MAP["1188"]="writingdesk_0130"
# SUBDIR_MAP["1215"]="writingdesk_0130"
# SUBDIR_MAP["1225"]="writingdesk_0130"
# SUBDIR_MAP["1239"]="writingdesk_0130"
# SUBDIR_MAP["1244"]="writingdesk_0130"
# SUBDIR_MAP["1275"]="writingdesk_0130"
# SUBDIR_MAP["1276"]="writingdesk_0130"
# SUBDIR_MAP["1277"]="writingdesk_0130"
# SUBDIR_MAP["1293"]="writingdesk_0130"
# SUBDIR_MAP["1294"]="writingdesk_0130"


# SUBDIR_MAP["1332"]="cctv"
# SUBDIR_MAP["1362"]="cctv"

# SUBDIR_MAP["1324"]="writingdesk_0203"


# SUBDIR_MAP["1225"]="writingdesk_0203"

# SUBDIR_MAP["1381"]="cctv"

# SUBDIR_MAP["1383"]="writingdesk_0212"
# SUBDIR_MAP["1384"]="writingdesk_0212"
# SUBDIR_MAP["1387"]="writingdesk_0212"
# SUBDIR_MAP["1440"]="writingdesk_0212"
# SUBDIR_MAP["1413"]="writingdesk_0212"


# SUBDIR_MAP["1497"]="cctv"


# SUBDIR_MAP["1562"]="cctv"
# SUBDIR_MAP["1581"]="cctv"
# SUBDIR_MAP["1768"]="cctv"


# SUBDIR_MAP["1769"]="cctv"
# SUBDIR_MAP["1923"]="cctv"



# SUBDIR_MAP["1562"]="skewer_0312"
# SUBDIR_MAP["1581"]="skewer_0312"
# SUBDIR_MAP["1768"]="skewer_0312"
# SUBDIR_MAP["1769"]="skewer_0312"
# SUBDIR_MAP["1923"]="skewer_0312"


# SUBDIR_MAP["2291"]="skewer_0316"
# SUBDIR_MAP["2292"]="skewer_0316"


# SUBDIR_MAP["2379"]="skewer_0317"
# SUBDIR_MAP["2050"]="udas_transfre_teleop_WipeTable"
# SUBDIR_MAP["2432"]="udas_transfre_teleop_WipeTable"
# SUBDIR_MAP["2547"]="udas_transfre_teleop_WipeTable"
# SUBDIR_MAP["2548"]="udas_transfre_teleop_WipeTable"
# SUBDIR_MAP["2162"]="udas_transfre_teleop_WipeTable"

# SUBDIR_MAP["2162"]="udas_test_transfer"
# SUBDIR_MAP["2547"]="udas_test_transfer"
# SUBDIR_MAP["2548"]="udas_test_transfer"
# SUBDIR_MAP["2432"]="udas_test_transfer"
# SUBDIR_MAP["2050"]="udas_test_transfer"

# SUBDIR_MAP["2378"]="udas_Collectcrash_test"
# SUBDIR_MAP["2552"]="udas_Collectcrash_test"

# SUBDIR_MAP["2050"]="udas_udas_Wipetable_test"
# SUBDIR_MAP["2548"]="udas_udas_Wipetable_test"
# SUBDIR_MAP["2432"]="udas_udas_Wipetable_test"
# SUBDIR_MAP["2547"]="udas_udas_Wipetable_test"

# SUBDIR_MAP["2162"]="udas_Wipetable_test"
# SUBDIR_MAP["2553"]="udas_Wipetable_test"


# SUBDIR_MAP["2871"]="udas_Collectcrash_test"


# SUBDIR_MAP["441"]="yhyhyhyhyh"


# SUBDIR_MAP["2801"]="skewer_0322"

# SUBDIR_MAP["2817"]="skewer_0404"
# SUBDIR_MAP["2824"]="skewer_0404"


# SUBDIR_MAP["4122"]="skewer_0413"
# SUBDIR_MAP["4123"]="skewer_0413"
# SUBDIR_MAP["4243"]="skewer_0413"


# SUBDIR_MAP["4506"]="skewer_0413"

# SUBDIR_MAP["3452"]="CapsuleToy_0512"
# SUBDIR_MAP["4146"]="CapsuleToy_0512"
# SUBDIR_MAP["5485"]="CapsuleToy_0512"

# SUBDIR_MAP["1384"]="pick_place_no_reset"
# SUBDIR_MAP["1086"]="pick_place_no_reset"
# SUBDIR_MAP["1026"]="pick_place_no_reset"
# SUBDIR_MAP["1011"]="pick_place_no_reset"
# SUBDIR_MAP["851"]="pick_place_no_reset"


# SUBDIR_MAP["5039"]="test_dj"
# SUBDIR_MAP["5040"]="test_dj"
# SUBDIR_MAP["5042"]="test_dj"


# SUBDIR_MAP["5050"]="sortpill"


# SUBDIR_MAP["6038"]="sortpill_0506"
#SUBDIR_MAP["6037"]="sortpill_0510"
#SUBDIR_MAP["6255"]="sortpill_0510"
#SUBDIR_MAP["6538"]="sortpill_0510"
# SUBDIR_MAP["6667"]="sortpill_0510"
# SUBDIR_MAP["2378"]="udas_collect_trash_0511"
# SUBDIR_MAP["7067"]="sortpill_0519"


# SUBDIR_MAP["7184"]="Conveyor_0521"
# SUBDIR_MAP["7067"]="sortpill_0523_tmp"
# SUBDIR_MAP["7184"]="Conveyor_0525"
# SUBDIR_MAP["8303"]="Unlock_0529"


SUBDIR_MAP["8571"]="Rein/insertflower/testdata"








# 定义每个任务ID对应的设备号列表（可选，如果某个ID没有定义，会使用空字符串）
# 多个设备用空格分隔，例如: DEVICE_MAP["716"]="moz1-y05 moz1-y08 moz1-y13"
declare -A DEVICE_MAP
# DEVICE_MAP["742"]="moz1-k05"
# DEVICE_MAP["750"]="moz1-t04 moz1-y06"
# DEVICE_MAP["760"]="moz1-y15 moz1-y06"
# DEVICE_MAP["761"]="moz1-y15 moz1-y06"
# DEVICE_MAP["766"]="moz1-y15"

# DEVICE_MAP["774"]="moz1-y06 moz1-y04 moz1-y15"
# DEVICE_MAP["773"]="moz1-y07 moz1-k02"
# DEVICE_MAP["784"]="moz1-y06 moz1-y04"
# DEVICE_MAP["785"]="moz1-k02 moz1-y07"
# DEVICE_MAP["793"]="moz1-y08 moz1-y04 moz1-k05"
# DEVICE_MAP["795"]="moz1-y13 moz1-y10"
# DEVICE_MAP["794"]="moz1-y15 moz1-y05"

# DEVICE_MAP["801"]="moz1-y05 moz1-k02 moz1-y04 moz1-y08 moz1-t04"
# DEVICE_MAP["802"]="moz1-y05 moz1-y06 moz1-y07 moz1-y15 moz1-y27"
# DEVICE_MAP["803"]="moz1-y13 moz1-k05 moz1-t04 moz1-y06 moz1-y07"
# DEVICE_MAP["779"]="moz1-y13 moz1-y08"
# DEVICE_MAP["780"]="moz1-y04 moz1-k05"

# DEVICE_MAP["796"]="moz1-k02 moz1-y07"
# DEVICE_MAP["851"]="moz1-y15 moz1-y27 moz1-y28"
# DEVICE_MAP["869"]="moz1-y03 moz1-y04 moz1-k02 moz1-k05"

# DEVICE_MAP["877"]="moz1-y04 moz1-k02 moz1-k05 moz1-y03"

# DEVICE_MAP["875"]="moz1-y05 moz1-y06 moz1-y07"
# DEVICE_MAP["876"]="moz1-y15 moz1-y27 moz1-y28"


# DEVICE_MAP["1000"]="moz1-k02 moz1-y04 moz1-y05 moz1-y06 moz1-y08 moz1-y30"
# DEVICE_MAP["1011"]="moz1-k02 moz1-y04 moz1-y05 moz1-y06 moz1-y08"
# DEVICE_MAP["1014"]="moz1-y15 moz1-y28 moz1-y29 moz1-y30 moz1-y33 moz1-y35"
# DEVICE_MAP["1015"]="moz1-k05 moz1-y03 moz1-y28 moz1-y29 moz1-y30 moz1-y33 moz1-y35"
# DEVICE_MAP["1026"]="moz1-k02 moz1-k05 moz1-y03 moz1-y04"
# DEVICE_MAP["1028"]="moz1-y05 moz1-y06 moz1-y08 moz1-y13"


# DEVICE_MAP["1076"]="moz1-y08 moz1-y15 moz1-y29 moz1-y33"
# DEVICE_MAP["1077"]="moz1-y15 moz1-y28"


# DEVICE_MAP["823"]="moz1-k02 moz1-y07"






# 定义每个任务ID对应的 prompt（可选，如果某个ID没有定义，会使用默认值）
declare -A PROMPT_MAP
# PROMPT_MAP["393"]="Place three bottles into a triangle"
# PROMPT_MAP["247"]="Prompt for task 247"
# PROMPT_MAP["252"]="Prompt for task 252"

DEFAULT_PREFIX="/mnt/vepfs01/output"

# 默认 prompt（当某个任务ID在 PROMPT_MAP 中没有定义时使用）
DEFAULT_PROMPT="fold long-sleeved hoodie"


GROUP_BY_FEATURE=true


DOWNLOAD_DATASET=true
GENERATE_SAMPLE_WEIGHTS=true
GENERATE_PROMPT=false
FETCH_ANNOTATIONS=true
GENERATE_DATASET_STATISTICS=true

# 读取参数
PREFIX="${1:-$DEFAULT_PREFIX}"
BASE_OUTPUT_DIR="$PREFIX/yifeng/resources/frontdesk"

# 数据筛选选项
ANNOTATED_ONLY=true      # true: 只导出有标注的数据; false: 导出所有数据
INCLUDE_UNCHECKED=true    # true: 包含未质检的数据; false: 不包含未质检的数据
INVALID_ONLY=false        # true: 只导出质检不合格的数据; false: 不限制

# 安装 ffmpeg（只需执行一次）
bash -lc 'set -e; if ! command -v ffmpeg >/dev/null 2>&1; then (sudo -n apt-get update -y && sudo -n apt-get install -y ffmpeg) || (apt-get update -y && apt-get install -y ffmpeg) || true; fi; if ! command -v ffmpeg >/dev/null 2>&1; then mkdir -p "$HOME/.local/bin"; workdir=$(mktemp -d); cd "$workdir"; URL=https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz; if command -v curl >/dev/null 2>&1; then curl -L "$URL" -o ffmpeg.tar.xz; else wget -O ffmpeg.tar.xz "$URL"; fi; tar -xf ffmpeg.tar.xz; d=$(find . -maxdepth 1 -type d -name "ffmpeg-*-amd64-static" | head -n1); cp "$d/ffmpeg" "$HOME/.local/bin/ffmpeg"; chmod +x "$HOME/.local/bin/ffmpeg"; echo "Installed static ffmpeg to $HOME/.local/bin/ffmpeg"; fi; export PATH="$HOME/.local/bin:$PATH"; ffmpeg -version | head -n1 | cat; echo "Encoders (h264):"; ffmpeg -hide_banner -encoders 2>/dev/null | grep -E "libx264|h264" | cat'

# 循环处理每个任务 - 手动指定任务ID列表以确保按顺序处理
# 将所有任务ID存储到数组中
TASK_ID_LIST=("${!FILE_NAME_MAP[@]}")

# 先打印所有的任务ID用于调试
echo "============================================"
echo "所有配置的任务ID: ${TASK_ID_LIST[@]}"
echo "任务ID数量: ${#TASK_ID_LIST[@]}"
echo "============================================"

# 统计总任务数（任务ID x 设备数）
total_tasks=0
for TASK_IDS in "${TASK_ID_LIST[@]}"; do
    if [ -n "${DEVICE_MAP[$TASK_IDS]}" ]; then
        # 统计该任务的设备数量
        device_count=$(echo "${DEVICE_MAP[$TASK_IDS]}" | wc -w)
        total_tasks=$((total_tasks + device_count))
    else
        total_tasks=$((total_tasks + 1))
    fi
done

echo "============================================"
echo "总任务数: $total_tasks"
echo "============================================"

current_task=0

for TASK_IDS in "${TASK_ID_LIST[@]}"; do
    echo "DEBUG: 开始处理任务ID: $TASK_IDS"
    # 从关联数组获取对应的文件名
    FILE_NAME="${FILE_NAME_MAP[$TASK_IDS]}"

    # 从关联数组获取对应的子目录名，如果不存在则从文件名提取
    if [ -n "${SUBDIR_MAP[$TASK_IDS]}" ]; then
        SUBDIR="${SUBDIR_MAP[$TASK_IDS]}"
    else
        # 默认从文件名提取第二个下划线分隔的部分
        SUBDIR=$(echo "$FILE_NAME" | awk -F'_' '{print $2}')
    fi

    # 从关联数组获取对应的设备号列表
    if [ -n "${DEVICE_MAP[$TASK_IDS]}" ]; then
        DEVICE_LIST="${DEVICE_MAP[$TASK_IDS]}"
    else
        DEVICE_LIST=""
    fi

    # 从关联数组获取对应的 prompt，如果不存在则使用默认值
    if [ -n "${PROMPT_MAP[$TASK_IDS]}" ]; then
        PROMPT="${PROMPT_MAP[$TASK_IDS]}"
    else
        PROMPT="$DEFAULT_PROMPT"
    fi

    # 如果没有设备列表，创建一个占位符
    if [ -z "$DEVICE_LIST" ]; then
        DEVICE_LIST="__EMPTY__"
    fi

    # 对每个设备进行循环处理
    for DEVICE in $DEVICE_LIST; do
        current_task=$((current_task + 1))

        # 如果 DEVICE 是占位符，设置为空字符串
        if [ "$DEVICE" = "__EMPTY__" ]; then
            DEVICE=""
        fi

        echo "============================================"
        echo "Processing task $current_task/$total_tasks"
        echo "TASK_IDS: $TASK_IDS"
        echo "FILE_NAME: $FILE_NAME"
        echo "SUBDIR: $SUBDIR"
        echo "DEVICE: $DEVICE"
        echo "PROMPT: $PROMPT"
        echo "============================================"

        # 构建输出目录名称：ID_FILE_NAME_DEVICE
        if [ -n "$DEVICE" ]; then
            OUTPUT_DIR_NAME="${TASK_IDS}_${FILE_NAME}_${DEVICE}"
        else
            OUTPUT_DIR_NAME="${TASK_IDS}_${FILE_NAME}"
        fi

        # /mnt/vepfs01/output/yifeng/resources/frontdesk
        # 定义超参数
        # BASE_OUTPUT_DIR="$PREFIX/yuhang/dataset"
        OUTPUT_DIR="$BASE_OUTPUT_DIR/$SUBDIR/${OUTPUT_DIR_NAME}"
        SAMPLE_WEIGHTS_DIR="$BASE_OUTPUT_DIR/$SUBDIR"

        ########################################################################################
        ########################################################################################
        ########################################################################################

        if [ "$DOWNLOAD_DATASET" = true ]; then
            echo "Processing task IDs: $TASK_IDS"
            echo "Output directory: $OUTPUT_DIR"

            # 构建设备号参数（如果有的话）
            DEVICE_ARGS=""
            if [ -n "$DEVICE" ]; then
                DEVICE_ARGS="--capture-devices $DEVICE"
            fi

            # 构建数据筛选参数
            FILTER_ARGS=""
            if [ "$FETCH_ANNOTATIONS" = true ]; then
                FILTER_ARGS="$FILTER_ARGS --fetch-annotations"
            fi
            if [ "$ANNOTATED_ONLY" = true ]; then
                FILTER_ARGS="$FILTER_ARGS --annotated-only"
            fi
            if [ "$INCLUDE_UNCHECKED" = true ]; then
                FILTER_ARGS="$FILTER_ARGS --include-unchecked"
            fi
            if [ "$INVALID_ONLY" = true ]; then
                FILTER_ARGS="$FILTER_ARGS --invalid-only"
            fi

            GROUP_ARGS=""
            if [ "$GROUP_BY_FEATURE" = true ]; then
                GROUP_ARGS="$GROUP_ARGS --group-by-features"
            fi


            # 统一调用
            python3 $PREFIX/yifeng/resources/frontdesk/export_dataset_normal_text_feature_split.py \
            --task-ids $TASK_IDS \
            --output-dir $OUTPUT_DIR \
            --api-url https://quanta.i.spirit-ai.com \
            --use-tos-internal-endpoint \
            $DEVICE_ARGS \
            $FILTER_ARGS \
            $GROUP_ARGS
            # --visual-prompt-mode box_orihigh \
            # --recording-limit 100 \
            # --no-recompute-vp-stats \
            # --only-text \
            # --skip-download \
        fi

        ########################################################################################
        ########################################################################################
        ########################################################################################

        if [ "$GENERATE_SAMPLE_WEIGHTS" = true ]; then
            # 生成 sample weights 文件
            mkdir -p "$SAMPLE_WEIGHTS_DIR"

            # 构建 JSON 内容 - 使用任务ID_文件名_设备号作为key
            json_content="{\n    \"$OUTPUT_DIR_NAME\":1\n}"

            # 写入文件到 $BASE_OUTPUT_DIR/$SUBDIR/ID_FILE_NAME_DEVICE.json
            echo -e "$json_content" > "$SAMPLE_WEIGHTS_DIR/$OUTPUT_DIR_NAME.json"
            echo "Generated sample weights file: $SAMPLE_WEIGHTS_DIR/$OUTPUT_DIR_NAME.json"
        fi

        ########################################################################################
        ########################################################################################
        ########################################################################################

        if [ "$GENERATE_PROMPT" = true ]; then
            # 只写入 {"task_index": 0, "task": "..."} 这一行到 tasks.jsonl，覆盖原有内容
            tasks_jsonl_path="$OUTPUT_DIR/meta/tasks.jsonl"

            if [ -f "$tasks_jsonl_path" ]; then
                echo "{\"task_index\": 0, \"task\": \"${PROMPT}\"}" > "$tasks_jsonl_path"
                echo "Overwritten with single JSON object: $tasks_jsonl_path"
            else
                echo "Warning: tasks.jsonl not found: $tasks_jsonl_path" >&2
            fi
        fi

        ########################################################################################
        ########################################################################################
        ########################################################################################

        echo "Completed task: $OUTPUT_DIR_NAME"
        echo ""
    done  # 结束设备循环
done  # 结束任务ID循环

echo "============================================"
echo "All tasks completed! Total: $current_task tasks"
echo "============================================"
