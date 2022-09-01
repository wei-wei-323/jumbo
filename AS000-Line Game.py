from numba import jit

import random
import math
import os
import multiprocessing
import common.DataExport as de
import common.InputSettings as inp
import DefineSymbols as defs

global arr_parsheet #遊戲Parsheet
global arr_pays #遊戲Pays
global arr_lines #遊戲Lines
folder_path = os.path.dirname(os.path.abspath('D:/jumbo/3_Money_Link/simulation/0')) #此層資料夾位置
global float_estimate_rtp #理論值RTP(用於計算標準差)
global bool_survival_mode #生存模式開關
global triggerLimit # 免費遊戲場次上限
global arr_get_freespins #免費遊戲觸發場次
global arr_window_reel_settings #遊戲結構
global bool_show_log #log開關
global int_extrafree_denominator
global int_extrafree_numerator
#------------------輸入參數------------------
getSettings = inp.inputbox()
bool_show_log = getSettings[1]
bool_survival_mode = getSettings[2]
arr_parsheet = de.GetFromExcel(folder_path+'/StripTable.xlsx',['Regular','Free'], False, np.int8)
arr_pays = de.GetFromExcel(folder_path+'/Pays.xlsx',['Regular','Free'], True, np.int32)
arr_lines = de.GetFromExcel(folder_path+'/common/Lines.xlsx',['30Line-A'], True, np.int8)
exportfileName = 'AS000'
float_estimate_rtp = 0.960000
Bet = 50
triggerLimit = 30 # free game condition
arr_get_freespins = np.array([[0,10,15,20],[0,5,0,0]],np.int8) # scatter condition[[base game],[free game]]-->[C1x2,C1x3,C1x4,C1x5]
arr_window_reel_settings = np.array([[3,5],[3,5]],np.int8) # reel condition [window, reel]
int_extrafree_denominator = 100000000
int_extrafree_numerator = 0
#------------------輸入參數------------------
#------------------自動計算遊戲內所需參數------------------
global int_cpu #cpu數量(用於自動分配執行緒)
global arr_bet_value #生存模式要跑的所有押注
global arr_bet_multiplier #對應不同押注反算出倍率
global arr_start_credit #生存模式的入鈔狀態
int_cpu = multiprocessing.cpu_count()
arr_bet_value = np.array([50,100,150,200,300,500,700,1000],np.int16)
arr_bet_multiplier = np.zeros(arr_bet_value.shape[0],np.float64)
for iBet in range(len(arr_bet_value)):
    arr_bet_multiplier[iBet] = arr_bet_value[iBet] / Bet
arr_start_credit = np.array([19526,39589,65944,132630,185951,332105,424757,770084],np.int64)
TotalRound = getSettings[0]
global do_not_check_List
do_not_check_List = np.array([defs.C1,defs.C2,defs.C3],np.int8)
int_parsheet_counts = arr_parsheet.shape[0]
global arr_parsheet_length
arr_parsheet_length = np.zeros((int_parsheet_counts,arr_window_reel_settings[0][1]),np.int16)
global int_number_of_lines
int_number_of_lines = arr_lines.shape[0]
global thresholdMultiple
thresholdMultiple = np.array([0,0,0.5,1,2,3,4,5,6,7,8,9,10,15,20,25,30,35,40,45,50,60,70,80,90,100,125,150,175,200,225,250,275,300,325,350,375,400,425,450,475,500,600,700,800,900,1000,2000,3000,4000,5000,6000,7000,8000,9000,10000,12000,14000,16000,18000,20000,22000,24000,26000,28000,30000,35000,40000,99999],np.float64)
for sheets in range(int_parsheet_counts):
    for iReel in range(arr_parsheet[sheets].shape[0]):
        arr_parsheet_length[sheets][iReel] = np.count_nonzero(arr_parsheet[sheets][iReel] != -1)
#自動分析C1位置
global arr_c1_in_reel
arr_c1_in_reel = np.zeros(arr_window_reel_settings[0][1],np.int16)
total_temp_rng = []
for iReel in range(arr_window_reel_settings[0][1]):
    arr_temp_rng = []
    for iSymbol in range(arr_parsheet_length[0][iReel]):
        bool_if_c1_appear = False
        for i in range(arr_window_reel_settings[0][0]):
            if iSymbol - i < 0:
                checking_symbol = arr_parsheet[0][iReel][arr_parsheet_length[0][iReel] + iSymbol - i]
            else:
                checking_symbol = arr_parsheet[0][iReel][iSymbol - i]
            if checking_symbol == defs.C1:
                bool_if_c1_appear = True
        if bool_if_c1_appear == True:
            arr_temp_rng.append(iSymbol)
    if arr_temp_rng != []:
        arr_c1_in_reel[iReel] = len(arr_temp_rng)
    total_temp_rng.append(arr_temp_rng)
global arr_force_c1_parsheet
arr_force_c1_parsheet = np.zeros((arr_window_reel_settings[0][1],max(arr_c1_in_reel)),np.int16)
for iReel in range(arr_window_reel_settings[0][1]):
    for iSymbol in range(arr_c1_in_reel[iReel]):
        arr_force_c1_parsheet[iReel][iSymbol] = total_temp_rng[iReel][iSymbol]
global int_c1_status
int_c1_status = np.count_nonzero(arr_c1_in_reel)
#------------------自動計算遊戲內所需參數------------------
# jit decorator tells Numba to compile this function.
# The argument types will be inferred by Numba when function is called.
@jit(['void(float64[:,:],int8,int64,int8)'], nopython=True, nogil=True)
def Main(arr_output_data,int_thread,int_rounds,int_bet_indicator):
    """
    遊戲主結構
    """
    if int_thread == 0:
        if bool_survival_mode == True:
            print('Survival Mode: On')
        else:
            print('Survival Mode: Off')
    #------------------define public variant start------------------
    #define result array
    WinsReport = arr_output_data[0]
        #WinsReport[0] = total spins
        #WinsReport[1] = total free spins
        #WinsReport[2] = mystery free game hits
        #WinsReport[3] = base hits
        #WinsReport[4] = free hits
        #WinsReport[5] = single max payment
        #WinsReport[6] = -
        #WinsReport[7] = -
        #WinsReport[8] = -
        #WinsReport[9] = -
        #WinsReport[10] = Standard deviation ^ 2
    HitsReport_Base = arr_output_data[1]
    HitsReport_Free = arr_output_data[2]
    PayReport_Base = arr_output_data[3]
    PayReport_Free = arr_output_data[4]
    # arr_output_data[5] #Base Game贏分區間表
    # arr_output_data[6] #Free Game贏分區間表
    # arr_output_data[7] #生存模式Coin In報表
    # arr_output_data[8] #生存模式Free Spin次數報表
    # arr_output_data[9] #生存模式剩餘分數報表
    # arr_output_data[10] #生存模式最大贏分區間表
    len_report = HitsReport_Base.shape[0]
    temp_HitsReport = np.zeros(len_report,np.int64)
    temp_PayReport = np.zeros(len_report,np.float64)
    arr_jumbo_rng = np.zeros(arr_window_reel_settings[0][1],np.int16)
    arr_result_reel = np.full((2,arr_window_reel_settings[1][0],arr_window_reel_settings[1][1]),-1,np.int8) #結果盤面
    arr_trigger_condition = np.zeros((2,2), np.int8) #[幾個C1進去,場次]
    arr_scatter_pay = np.zeros(2,np.float64) #[base scatter pay,free scatte pay]
    arr_wins = np.zeros(2,np.float64) #[Base Game贏分,Free Game贏分]
    arr_freegame_status = np.zeros(1,np.int8)
    arr_line_wins = np.zeros(2,np.float64) #[current_payment,higher_payment]
    arr_force_reel_status = np.array([1,1,1,0,0],np.bool_) #若有5C1時shuffle過後為強制進入free game的C1位置
    #------------------define public variant end------------------
    def calculate_std(dtWins):
        """
        計算標準差
        """
        net_pay = dtWins - arr_bet_value[int_bet_indicator]
        ev = (float_estimate_rtp - 1) * arr_bet_value[int_bet_indicator]
        distance_to_mean = net_pay - ev
        WinsReport[10] += np.square(distance_to_mean)

    def dice_from_array(arr_parameters):
        """
        從cumsum遞增數列當中擲骰結果
        """
        int_temp_dice = math.ceil(np.random.random() * np.max(arr_parameters))
        for i in range(arr_parameters.shape[0]):
            if int_temp_dice <= arr_parameters[i]:
                return i
        return -1

    def count_1D_array(arr_processing_reel,dtTarget,bool_isequal=True):
        """
        統計一維陣列指定Target的數量
        """
        temp_count = 0
        for i in range(arr_processing_reel.shape[0]):
            if bool_isequal == True:
                if arr_processing_reel[i] == dtTarget:
                    temp_count += 1
            else:
                if arr_processing_reel[i] != dtTarget:
                    temp_count += 1
        return temp_count

    def count_2D_array(arr_processing_reel,dtTarget,bool_isequal=True):
        """
        統計二維陣列指定Target的數量
        """
        temp_count = 0
        for i in range(arr_processing_reel.shape[0]):
            for j in range(arr_processing_reel.shape[1]):
                if bool_isequal == True:
                    if arr_processing_reel[i][j] == dtTarget:
                        temp_count += 1
                else:
                    if arr_processing_reel[i][j] != dtTarget:
                        temp_count += 1
        return temp_count

    def np_isin(np_list,np_target):
        """
        判斷Target是否存在於輸入的List列表內
        """
        w = np_list.shape[0]
        inStatus = False
        for item in range(w):
            if np_list[item] == -1:
                break
            elif np_list[item] == np_target:
                inStatus = True
                break
        return inStatus

    def np_equal(np_list,np_target):
        """
        判斷兩個一維陣列是否完全相等
        """
        inStatus = True
        for item in range(np_list.shape[0]):
            if np_list[item] != np_target[item]:
                inStatus = False
        return inStatus

    def initial_2D_array(arr_arrays,var_value=0):
        """
        初始化二維陣列
        """
        for i in range(arr_arrays.shape[0]):
            for j in range(arr_arrays.shape[1]):
                arr_arrays[i][j] = var_value

    def initial_1D_array(arr_arrays,var_value=0):
        """
        初始化一維陣列
        """
        for i in range(arr_arrays.shape[0]):
            arr_arrays[i] = var_value

    def initial_temp_Report():
        """
        初始化temp_Report
        """
        for item in range(len_report):
            temp_HitsReport[item] = 0
            temp_PayReport[item] = 0

    def Add_temp_report(arr_processing_hitreport,arr_processing_payreport):
        """
        把暫存的hit與pay報表加入正式統計的報表內(因為有些算分狀況可能需要被拋棄，所以必須確認是要計入算分的狀態才合併入正式報表)
        """
        arr_processing_hitreport += temp_HitsReport
        arr_processing_payreport += temp_PayReport
        WinsReport[5] = max(WinsReport[5],np.sum(temp_PayReport))
        initial_temp_Report()

    def go_record(dtValue,dtThreshold,dtRecord):
        """
        紀錄統計區間
        """
        dtLen = len(dtThreshold) - 1
        for iThres in range(dtLen):
            if dtThreshold[iThres] == dtThreshold[iThres+1]:
                if dtThreshold[iThres] == dtValue:
                    dtRecord[iThres] += 1
                    break
            else:
                if dtThreshold[iThres] < dtValue <= dtThreshold[iThres+1]:
                    dtRecord[iThres] += 1
                    break

    def GetReelResult(bool_isfreegame,int_processing_parsheet): # get the whole reel result
        """
        依據arr_jumbo_rng取出盤面
        """
        for iReel in range(arr_window_reel_settings[bool_isfreegame][1]):
            for iSymbol in range(arr_window_reel_settings[bool_isfreegame][0]):
                if arr_jumbo_rng[iReel] - iSymbol < 0:
                    arr_result_reel[bool_isfreegame][iSymbol][iReel] = arr_parsheet[int_processing_parsheet][iReel][arr_parsheet_length[int_processing_parsheet][iReel] + arr_jumbo_rng[iReel] - iSymbol]
                else:
                    arr_result_reel[bool_isfreegame][iSymbol][iReel] = arr_parsheet[int_processing_parsheet][iReel][arr_jumbo_rng[iReel] - iSymbol]

    def GetRND(int_processing_parsheet):
        """
        取出RNG
        ex:[1,4,87,78,54]
        """
        for iReel in range(arr_parsheet[int_processing_parsheet].shape[0]):
            arr_jumbo_rng[iReel] = math.ceil(np.random.random() * arr_parsheet_length[int_processing_parsheet][iReel]) - 1

    def Get3C1RND():
        if int_c1_status == 5:
            np.random.shuffle(arr_force_reel_status)
            if bool_show_log == True:print(arr_force_reel_status)
            for iReel in range(arr_window_reel_settings[0][1]):
                if arr_force_reel_status[iReel] == True:
                    int_temp_dice = math.ceil(np.random.random() * arr_c1_in_reel[iReel])-1
                    arr_jumbo_rng[iReel] = arr_force_c1_parsheet[iReel][int_temp_dice]
                else:
                    while True:
                        arr_jumbo_rng[iReel] = math.ceil(np.random.random() * arr_parsheet_length[0][iReel])-1
                        if np_isin(arr_force_c1_parsheet[iReel],arr_jumbo_rng[iReel]) == False:
                            break
        else:
            for iReel in range(arr_window_reel_settings[0][1]):
                if arr_c1_in_reel[iReel] > 0:
                    int_temp_dice = math.ceil(np.random.random() * arr_c1_in_reel[iReel])-1
                    arr_jumbo_rng[iReel] = arr_force_c1_parsheet[iReel][int_temp_dice]
                else:
                    arr_jumbo_rng[iReel] = math.ceil(np.random.random() * arr_parsheet_length[0][iReel])-1

    def CheckScatter(bool_isfreegame):
        """
        檢查Free Game是否觸發
        """
        initial_1D_array(arr_trigger_condition[bool_isfreegame])
        arr_scatter_pay[bool_isfreegame] = 0
        arr_trigger_condition[bool_isfreegame][0] = count_2D_array(arr_result_reel[bool_isfreegame],defs.C1)
        if arr_trigger_condition[bool_isfreegame][0] >= 2:
            record_symbol = arr_trigger_condition[bool_isfreegame][0] - 2
            if arr_get_freespins[bool_isfreegame][record_symbol] > 0 or arr_pays[bool_isfreegame][defs.C1][record_symbol] > 0:
                arr_scatter_pay[bool_isfreegame] = arr_pays[bool_isfreegame][defs.C1][record_symbol] * arr_bet_value[int_bet_indicator]
                arr_trigger_condition[bool_isfreegame][1] = arr_get_freespins[bool_isfreegame][record_symbol]

    def CheckWin(bool_isfreegame):
        """
        檢查贏分
        """
        temp_hit = 0
        if bool_show_log == True:
            print('--')
            for iWindow in range(arr_window_reel_settings[bool_isfreegame][0]):
                print(arr_result_reel[bool_isfreegame][arr_window_reel_settings[bool_isfreegame][0] - iWindow - 1])
            print('--')
        for iLine in range(int_number_of_lines):
            higher_symbol = 0
            higher_count = 0
            match_count = 1
            #get main_symbol first
            main_symbol = arr_result_reel[bool_isfreegame][arr_lines[iLine][0]][0]
            if np_isin(do_not_check_List,main_symbol) == False:
                for iReel in range(1,arr_window_reel_settings[bool_isfreegame][1]):
                    checking_symbol = arr_result_reel[bool_isfreegame][arr_lines[iLine][iReel]][iReel]
                    #check connect
                    if np_isin(defs.WS[main_symbol],checking_symbol) == True:
                        match_count += 1 #if connected
                        if main_symbol == defs.WW and checking_symbol != defs.WW and checking_symbol != defs.C2: #if need to change main_symbol
                            main_symbol = checking_symbol
                    else:
                        break #if not connected
                    # checking payment at least 2 symbol connected
                    if match_count >= 2:
                        arr_line_wins[0] = arr_pays[bool_isfreegame][main_symbol][match_count-2] * arr_bet_multiplier[int_bet_indicator]
                        #get the highest payment
                        if arr_line_wins[0] > 0 and arr_line_wins[0] >= arr_line_wins[1]:
                            arr_line_wins[1] = arr_line_wins[0]
                            higher_count = match_count
                            higher_symbol = main_symbol
            #return highest payment and symbol
            if arr_line_wins[1] > 0:
                temp_hit = 1
                record_symbol = 4 * higher_symbol + higher_count - 2
                temp_HitsReport[record_symbol] += 1
                temp_PayReport[record_symbol] += arr_line_wins[1]
                #print win line
                if bool_show_log == True:
                    print(('Line',iLine+1,'Symbol',higher_symbol,'Count',higher_count,'Payment',arr_line_wins[1]))
            initial_1D_array(arr_line_wins)
        WinsReport[3+bool_isfreegame] += temp_hit

    def BaseGame():
        """
        Base Game遊戲流程
        """
        WinsReport[0] += 1 #record total base spins
        #step1. dice rnd
        temp_dice_rnd = math.ceil(np.random.random() * int_extrafree_denominator)
        if temp_dice_rnd <= int_extrafree_numerator:
            Get3C1RND()
        else:
            GetRND(0)
        GetReelResult(0,0)
        #step2. check scatter
        CheckScatter(0)
        #step2. check wins
        CheckWin(0)
        arr_wins[0] = np.sum(temp_PayReport)
        Add_temp_report(HitsReport_Base,PayReport_Base)

    def FreeGame():
        """
        Free Game遊戲流程
        """
        freespin = 0
        arr_wins[1] += arr_scatter_pay[0]
        #base game trigger free game算在base game hits裡
        HitsReport_Base[4 * defs.C1 + arr_trigger_condition[0][0] - 2] += 1
        #base game scatter pay要算在free game贏分裡面
        PayReport_Free[4 * defs.C1 + arr_trigger_condition[0][0] - 2] += arr_scatter_pay[0]
        while arr_trigger_condition[0][1] > 0:
            arr_trigger_condition[0][1] -= 1
            freespin += 1
            WinsReport[1] += 1
            if bool_show_log == True:
                print('---------------------------')
                print('Free Spin',freespin)
            GetRND(1)
            GetReelResult(1,1)
            CheckScatter(1)
            CheckWin(1)
            if arr_trigger_condition[1][1] > 0:
                arr_trigger_condition[0][1] += arr_trigger_condition[1][1]
                temp_HitsReport[4 * defs.C1 + arr_trigger_condition[1][0] - 2] += 1
                temp_PayReport[4 * defs.C1 + arr_trigger_condition[1][0] - 2] += arr_scatter_pay[1]
            arr_wins[1] += np.sum(temp_PayReport)
            Add_temp_report(HitsReport_Free,PayReport_Free)
            if bool_show_log == True:
                print('Total Free Wins=', arr_wins[1])
            if freespin == triggerLimit:
                break
        go_record(arr_wins[1]/arr_bet_value[int_bet_indicator], thresholdMultiple, arr_output_data[6])

    def SpinGame():
        """
        單次Spin流程
        """
        #step1. 玩Base Game
        BaseGame()
        if arr_trigger_condition[0][1] > 0: #如果有觸發Free Game的話
            #step2. 玩Free Game
            FreeGame()
            arr_freegame_status[0] = 1
        go_record((arr_wins[0] + arr_wins[1])/arr_bet_value[int_bet_indicator], thresholdMultiple, arr_output_data[5])
        return arr_wins[0] + arr_wins[1],  arr_freegame_status[0] #return 總贏分,進入free game(0次/1次)

    #區分生存模式與單次spin模式與迴圈
    for dr in range(int_rounds):
        checkpoint = int_rounds // 10
        if int_thread == int_cpu-1 and dr % checkpoint == 0: #print進度
            print((dr // checkpoint)*10,'%')
        if bool_show_log == True:
            print('--')
            print('Spin', dr+1)
        if bool_survival_mode == True:
            total_credit = 0
            freeSpinRecord = 0
            total_spin = 0
            max_win_ratio = 0
            start_credit = arr_start_credit[int_bet_indicator]
            while start_credit >= arr_bet_value[int_bet_indicator] and total_spin < 2160:#沒錢或達到每人平均轉數離開
                total_spin += 1
                start_credit -= arr_bet_value[int_bet_indicator]
                total_credit += arr_bet_value[int_bet_indicator]
                totalWins, myFreeSpins = SpinGame() #單次spin game
                calculate_std(totalWins)
                start_credit += totalWins
                freeSpinRecord += myFreeSpins
                max_win_ratio = max(max_win_ratio,totalWins/arr_bet_value[int_bet_indicator])
                #---初始化所有需要初始化的變數---
                initial_1D_array(arr_wins)
                arr_freegame_status[0] = 0
                #---初始化所有需要初始化的變數---
            if start_credit < arr_bet_value[int_bet_indicator]:
                start_credit = 0
            go_record(total_credit/10000, thresholdMultiple, arr_output_data[7])
            go_record(freeSpinRecord, thresholdMultiple, arr_output_data[8])
            go_record(start_credit/10000, thresholdMultiple, arr_output_data[9])
            go_record(max_win_ratio, thresholdMultiple, arr_output_data[10])
        else:
            totalWins, myFreeSpins = SpinGame()
            calculate_std(totalWins)
            #---初始化所有需要初始化的變數---
            initial_1D_array(arr_wins)
            arr_freegame_status[0] = 0
            #---初始化所有需要初始化的變數---

lenMultiplier = len(arr_bet_multiplier)
arr_combine_report = []
for int_bet_indicator in range(lenMultiplier):
    if bool_survival_mode == True:
        opfileName = folder_path+'/'+exportfileName + ' BET-' + str(arr_bet_value[int_bet_indicator])
        arr_combine_report.append(opfileName+'.xls')
    else:
        opfileName = folder_path+'/'+exportfileName
    print('-------')
    print('BET: %d' % (arr_bet_value[int_bet_indicator]))
    # make multi-thread
    func_nb_mt = de.make_multithread(Main,TotalRound)
    finalReport, finialDuration = de.timefunc("Duration: ",func_nb_mt,int_bet_indicator)
    #export report
    de.DataExport(opfileName + '.xls',finalReport,finialDuration,arr_bet_value[int_bet_indicator],float_estimate_rtp)
    if bool_survival_mode == False:
        break
if bool_survival_mode == True and len(arr_combine_report) > 0:
    de.combine_files(arr_combine_report,'allRawData.csv')