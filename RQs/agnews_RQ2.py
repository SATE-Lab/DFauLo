import copy
import os
import pickle
import random

import numpy as np
import pandas as pd
import torch
import xlwt
from matplotlib import pyplot as plt
from sklearn.linear_model import LogisticRegression
from torch import nn
from torch.autograd.grad_mode import F
from torch.utils.data import TensorDataset
from tqdm import tqdm

from myvocab import Vocab
from torchtext.data.utils import get_tokenizer
from train_model.models import LSTM, BiLSTM

vocab = pickle.load(open("./data/AgNews/vocab.pkl", "rb"))

device = "cuda"


def PoBL(ranklist, ratio):
    n = ranklist.shape[0]
    m = 0
    for i in range(n):
        if ranklist[i][0] == 1:
            m += 1
    cnt = 0
    for i in range(int(n * ratio)):
        if ranklist[i][0] == 1:
            cnt += 1
    # print('PoBL score: ', cnt / m)
    return cnt / m


def RAUC(ranklist, bestlist):
    rat = [x for x in range(101)]
    y = []
    yb = []
    for i in rat:
        y.append(PoBL(ranklist, i / 100.) * 100)
        yb.append(PoBL(bestlist, i / 100.) * 100)
    colorlist = ['violet', 'green', 'red', 'hotpink', 'mediumblue', 'orange', 'yellow', 'yellowgreen', 'peachpuff']
    # plt.plot(rat, y, color=colorlist[PCNT], label=str(PCNT + 1))
    # if PCNT==0:
    # plt.plot(rat, yb, color='blue', label='best')
    # plt.legend()
    # if PCNT==PALL-1:
    # plt.show()
    # print("RAUC score: ", np.trapz(y, rat) / np.trapz(yb, rat))
    return np.trapz(y, rat) / np.trapz(yb, rat)


def bestAUC(ranklist):
    bestlist = []
    for i in range(ranklist.shape[0]):
        if ranklist[i][0] == 1:
            bestlist.append(ranklist[i])
    for i in range(ranklist.shape[0]):
        if ranklist[i][0] == 0:
            bestlist.append(ranklist[i])
    bestlist = np.array(bestlist)
    return bestlist


def EXAM_F(ranklist):
    n = ranklist.shape[0]
    pos = -1
    for i in range(n):
        if ranklist[i][0] == 1:
            pos = i
            break
    return (pos + 1) / n
    # print('EXAM_F score: ', (pos + 1) / n)


def EXAM_L(ranklist):
    n = ranklist.shape[0]
    pos = -1
    for i in range(n - 1, -1, -1):
        if ranklist[i][0] == 1:
            pos = i
            break
    return (pos + 1) / n
    # print('EXAM_L score: ', (pos + 1) / n)


def EXAM_AVG(ranklist):
    n = ranklist.shape[0]
    m = 0
    tf = 0
    for i in range(n):
        if ranklist[i][0] == 1:
            tf += i
            m += 1
    return tf / (n * m)
    # print('EXAM_AVG score: ', tf / (n * m))


def APFD(ranklist):
    n = ranklist.shape[0]
    m = 0
    tf = 0
    for i in range(n):
        if ranklist[i][0] == 1:
            tf += i
            m += 1

    # print('APFD score: ', 1 - (tf / (n * m)) + (1 / (2 * n)))
    return 1 - (tf / (n * m)) + (1 / (2 * n))


def getlockmodelLSTM(modelpath):
    premodel = LSTM(voc_len=len(vocab), PAD=vocab.PAD)

    state_dict = torch.load(modelpath)
    premodel.load_state_dict(state_dict)
    for param in premodel.parameters():
        param.requires_grad = False

    premodel.fc1 = nn.Linear(128, 64)
    premodel.fc2 = nn.Linear(64, 4)

    return premodel


def getlockmodelBiLSTM(modelpath):
    premodel = BiLSTM(voc_len=len(vocab), PAD=vocab.PAD)

    state_dict = torch.load(modelpath)
    premodel.load_state_dict(state_dict)
    for param in premodel.parameters():
        param.requires_grad = False

    premodel.fc1 = nn.Linear(128 * 2, 128)
    premodel.fc2 = nn.Linear(128, 4)

    return premodel


def getOUTPUT(model, datapath):
    predata = np.load(datapath, allow_pickle=True)
    x_train = torch.from_numpy(np.array([x for x in predata[:, 1]]))
    y_train = torch.from_numpy(np.array([int(x) for x in predata[:, 0]]))

    loss_fn = nn.CrossEntropyLoss()  # 交叉熵损失
    model.to(device)
    model.eval()
    sfout = []
    softmax_func = nn.Softmax(dim=1)
    losslst = []
    with torch.no_grad():
        for i in tqdm(range(x_train.shape[0])):
            X = x_train[i].reshape(1, -1)
            X = X.to(device)

            y = y_train[i].reshape(1)
            y = y.long()
            y = y.to(device)

            output = model(X)

            soft_output = softmax_func(output)

            cur_loss = loss_fn(soft_output, y)

            soft_output = soft_output.cpu()
            cur_loss = cur_loss.cpu()
            sfout.append(soft_output.numpy()[0])
            losslst.append(cur_loss)
    losslst = np.array(losslst)
    sfout = np.array(sfout)
    return sfout, losslst


def getGT(datapath):
    predata = np.load(datapath, allow_pickle=True)
    y_train = torch.from_numpy(np.array([int(x) for x in predata[:, 0]]))

    GTsf = []
    for i in range(y_train.shape[0]):
        tmp = [0, 0, 0, 0]
        tmp[int(y_train[i])] = 1
        GTsf.append(tmp)

    GTsf = np.array(GTsf)

    return GTsf


def get_featureV(datapath, orgsfm, GTsfm, S1sfm, S2sfm, S3sfm, orgloss, S1loss, S2loss, S3loss, suslist, datatype,
                 modeltype, dataratio):
    trainarr = np.load(datapath, allow_pickle=True)
    is_dirty = torch.from_numpy(np.array([int(x) for x in trainarr[:, 2]]))
    feaV = []
    for i in range(is_dirty.shape[0]):
        tmp = []
        for j in range(4):
            tmp.append(orgsfm[i][j])
        for j in range(4):
            tmp.append(GTsfm[i][j])
        for j in range(4):
            tmp.append(S1sfm[i][j])
        for j in range(4):
            tmp.append(S2sfm[i][j])
        for j in range(4):
            tmp.append(S3sfm[i][j])
        tmp.append(int(trainarr[i][3]))
        tmp.append(int(trainarr[i][4]))
        tmp.append(int(trainarr[i][5]))
        tmp.append(orgloss[i])
        tmp.append(S1loss[i])
        tmp.append(S2loss[i])
        tmp.append(S3loss[i])
        tmp.append(suslist[i])
        tmp.append(int(is_dirty[i]))
        feaV.append(tmp)

    feaV = np.array(feaV)
    np.save('F:/ICSEdata/feature/' + dataratio + '_' + datatype + '_feature_' + modeltype + '.npy', feaV)


def get_susp_rank_res(suslist, is_dirty):
    rank = []
    for i in range(is_dirty.shape[0]):
        rank.append([int(is_dirty[i]), float(suslist[i])])
    rank = np.array(rank)
    rank = rank[rank[:, 1].argsort()[::-1]]
    print(rank)
    print("rank shape: ", rank.shape)
    RAUC(rank, bestAUC(rank))
    EXAM_F(rank)
    EXAM_L(rank)
    EXAM_AVG(rank)
    PoBL(rank, 0.1)
    APFD(rank)


def getmodelout(model, X, Y):
    model.eval()
    sfout = []
    softmax_func = nn.Softmax(dim=1)
    X = torch.from_numpy(X)
    X = X.int()

    with torch.no_grad():
        out = model(X)
        soft_output = softmax_func(out)
        sfout.append(soft_output.numpy()[0])

    sfout = np.array(sfout)
    return sfout


def getransusp(orgmodel, S1model, S2model, S3model, X, Y):
    orgmodel.eval()
    S1model.eval()
    S2model.eval()
    S3model.eval()
    loss_fn = nn.CrossEntropyLoss()  # 交叉熵损失
    X = torch.from_numpy(X)
    X = X.int()
    orglist = []
    S1list = []
    S2list = []
    S3list = []

    with torch.no_grad():
        y = []
        y.append(Y)
        y = np.array(y)
        y = torch.from_numpy(y)
        y = y.long()

        softmax_func = nn.Softmax(dim=1)
        org_out = softmax_func(orgmodel(X))
        S1_out = softmax_func(S1model(X))
        S2_out = softmax_func(S2model(X))
        S3_out = softmax_func(S3model(X))

        org_loss = loss_fn(org_out, y)
        S1_loss = loss_fn(S1_out, y)
        S2_loss = loss_fn(S2_out, y)
        S3_loss = loss_fn(S3_out, y)

        orglist.append(org_loss.item())
        S1list.append(S1_loss.item())
        S2list.append(S2_loss.item())
        S3list.append(S3_loss.item())

    return orglist, S1list, S2list, S3list


# 95805
def getrandomdata(modeltype, datatype, lb, ablation):
    X = np.zeros((1, 100))
    # print(X.shape)
    for i in range(100):
        X[0][i] = random.randint(0, 95804)
    Y = lb

    if modeltype == 'LSTM':
        orgmodel = LSTM(voc_len=len(vocab), PAD=vocab.PAD)
        S1model = LSTM(voc_len=len(vocab), PAD=vocab.PAD)
        S2model = LSTM(voc_len=len(vocab), PAD=vocab.PAD)
        S3model = LSTM(voc_len=len(vocab), PAD=vocab.PAD)

        orgstate_dict = torch.load('./models/agnews_' + datatype + '_LSTM.pth')
        orgmodel.load_state_dict(orgstate_dict)

        S1state_dict = torch.load('./retrainmodel/agnews_' + datatype + '_LSTM_retrain_VAE.pth')
        S1model.load_state_dict(S1state_dict)

        S2state_dict = torch.load('./retrainmodel/agnews_' + datatype + '_LSTM_retrain_Kmeans.pth')
        S2model.load_state_dict(S2state_dict)

        S3state_dict = torch.load('./retrainmodel/agnews_' + datatype + '_LSTM_retrain_Confident.pth')
        S3model.load_state_dict(S3state_dict)
    elif modeltype == 'BiLSTM':
        orgmodel = BiLSTM(voc_len=len(vocab), PAD=vocab.PAD)
        S1model = BiLSTM(voc_len=len(vocab), PAD=vocab.PAD)
        S2model = BiLSTM(voc_len=len(vocab), PAD=vocab.PAD)
        S3model = BiLSTM(voc_len=len(vocab), PAD=vocab.PAD)

        orgstate_dict = torch.load('./models/agnews_' + datatype + '_BiLSTM.pth')
        orgmodel.load_state_dict(orgstate_dict)

        S1state_dict = torch.load('./retrainmodel/agnews_' + datatype + '_BiLSTM_retrain_VAE.pth')
        S1model.load_state_dict(S1state_dict)

        S2state_dict = torch.load('./retrainmodel/agnews_' + datatype + '_BiLSTM_retrain_Kmeans.pth')
        S2model.load_state_dict(S2state_dict)

        S3state_dict = torch.load('./retrainmodel/agnews_' + datatype + '_BILSTM_retrain_Confident.pth')
        S3model.load_state_dict(S3state_dict)

    orgsfm = getmodelout(orgmodel, X, Y)
    S1sfm = getmodelout(S1model, X, Y)
    GTsf = []

    tmp = [0, 0, 0, 0]
    tmp[int(Y)] = 1
    GTsf.append(tmp)
    GTsf = np.array(GTsf)
    S2sfm = getmodelout(S2model, X, Y)
    S3sfm = getmodelout(S3model, X, Y)
    orglist, S1list, S2list, S3list = getransusp(orgmodel, S1model, S2model, S3model, X, Y)

    fea = []
    for i in range(4):
        fea.append(orgsfm[0][i])
    for i in range(4):
        fea.append(GTsf[0][i])
    for i in range(4):
        fea.append(S1sfm[0][i])
    for i in range(4):
        fea.append(S2sfm[0][i])
    for i in range(4):
        fea.append(S3sfm[0][i])
    fea.append(1)
    fea.append(1)
    fea.append(1)
    fea.append(orglist[0])
    fea.append(S1list[0])
    fea.append(S2list[0])
    fea.append(S3list[0])

    fea = np.array(fea)
    # print(fea)
    if ablation == 'input':
        de = [x for x in range(12, 20)]
        de.append(21)
        de.append(22)
        de.append(25)
        de.append(26)
        fea = np.delete(fea, de, axis=0)
    elif ablation == 'hidden':
        de = [x for x in range(8, 12)]
        for i in range(16, 20):
            de.append(i)
        de.append(20)
        de.append(22)
        de.append(24)
        de.append(26)
        fea = np.delete(fea, de, axis=0)
    elif ablation == 'output':
        de = [x for x in range(8, 16)]
        de.append(20)
        de.append(21)
        de.append(24)
        de.append(25)
        fea = np.delete(fea, de, axis=0)
    elif ablation == 'input+hidden':
        de = [x for x in range(16, 20)]
        de.append(22)
        de.append(26)
        fea = np.delete(fea, de, axis=0)
    elif ablation == 'hidden+output':
        de = [x for x in range(8, 12)]
        de.append(20)
        de.append(24)
        fea = np.delete(fea, de, axis=0)
    elif ablation == 'input+output':
        de = [x for x in range(12, 26)]
        de.append(21)
        de.append(25)
        fea = np.delete(fea, de, axis=0)
    return fea


def AT(feaVec, modeltype, datatype, is_dirty, ablation):
    NUM = 100
    NUM2 = 4

    cnt = 0
    newfea = []
    tmpfea = copy.deepcopy(feaVec)
    ind = [x for x in range(tmpfea.shape[0])]
    random.shuffle(ind)
    tmpfea = tmpfea[ind]
    # for i in range(tmpfea.shape[0]):
    #     tmpfea[i], tmpfea[ind[i]] = tmpfea[ind[i]], tmpfea[i]

    for i in range(tmpfea.shape[0]):
        if cnt < NUM:  # and int(tmpfea[i][-1])==0:
            newfea.append(tmpfea[i][0:-2])
            cnt += 1
    for i in range(NUM2):
        newfea.append(getrandomdata(modeltype, datatype, i, ablation))

    newfea = np.array(newfea)
    # print(newfea.shape)

    Y = []
    for i in range(NUM):
        Y.append(0)
    for i in range(NUM2):
        Y.append(1)

    Y = np.array(Y)
    lg = LogisticRegression(C=1.0)
    lg.fit(newfea, Y)

    LRres = lg.predict_proba(feaVec[0:feaVec.shape[0], 0:-2])  ####@@@@
    LRres = LRres[:, 1]

    rank = []
    for i in range(is_dirty.shape[0]):
        rank.append([int(feaVec[i][-1]), float(LRres[i])])

    rank = np.array(rank)
    rank = rank[rank[:, 1].argsort()[::-1]]
    # print(rank)
    # print("rank shape: ", rank.shape)
    save3 = RAUC(rank, bestAUC(rank))
    f = EXAM_F(rank)
    l = EXAM_L(rank)
    avg = EXAM_AVG(rank)
    save1 = PoBL(rank, 0.1)
    save2 = APFD(rank)
    return save1, save2, save3, f, l, avg


def UPDATE(feaVec, modeltype, datatype, is_dirty):
    check_ratio = 0.25
    per_check = 50
    FIRST_NUM = 100

    check_num = int((0.25 - FIRST_NUM / feaVec.shape[0]) * (feaVec.shape[0] - FIRST_NUM))

    # 打乱
    ind = [x for x in range(feaVec.shape[0])]
    random.shuffle(ind)
    feaVec = feaVec[ind]
    # for i in range(feaVec.shape[0]):
    #     feaVec[i], feaVec[ind[i]] = feaVec[ind[i]], feaVec[i]

    # 第一次选择
    fea_start = feaVec[0:FIRST_NUM, :-2]
    lb_start = feaVec[0:FIRST_NUM, -1]
    print(lb_start.shape)
    if lb_start.sum() <= 2:
        newfea = []
        newlb = []
        for i in range(4):
            newfea.append(getrandomdata(modeltype, datatype, i))
            newlb.append(1)
        newfea = np.array(newfea)
        newlb = np.array(newlb)
        fea_start = np.vstack((fea_start, newfea))
        lb_start = np.concatenate((lb_start, newlb))
    print('fea_start shape: ', fea_start.shape)
    print('lb_start shape: ', lb_start.shape)
    fea_left = feaVec[FIRST_NUM:, :-2]
    lb_left = feaVec[FIRST_NUM:, -1]

    lg_st = LogisticRegression(C=1.0)
    lg_st.fit(fea_start, lb_start)

    LRres = lg_st.predict_proba(fea_left)  ####@@@@
    LRres = LRres[:, 1]

    fea_left = fea_left[LRres.argsort()[::-1]]
    lb_left = lb_left[LRres.argsort()[::-1]]

    X = copy.deepcopy(fea_start)
    Y = copy.deepcopy(lb_start)
    ##开始
    for i in range(int(check_num / per_check)):
        print(str(i) + '/' + str(int(check_num / per_check)))
        fea = fea_left[FIRST_NUM + i * per_check:FIRST_NUM + (i + 1) * per_check, :]
        lb = lb_left[FIRST_NUM + i * per_check:FIRST_NUM + (i + 1) * per_check]

        fea_left = fea_left[per_check:, :]
        lb_left = lb_left[per_check:]

        lg = LogisticRegression(C=1.0)
        X = np.vstack((X, fea))
        Y = np.concatenate((Y, lb))
        # print('X Y shape',X.shape,Y.shape)
        # print('fea_left shape',fea_left.shape)
        lg.fit(X, Y)

        LRres = lg.predict_proba(fea_left)  ####@@@@
        LRres = LRres[:, 1]

        fea_left = fea_left[LRres.argsort()[::-1]]
        lb_left = lb_left[LRres.argsort()[::-1]]

    ##结果统计
    LRres = lg.predict_proba(feaVec[:, :-2])  ####@@@@
    LRres = LRres[:, 1]

    rank = []
    for i in range(feaVec.shape[0]):
        rank.append([int(feaVec[i][-1]), float(LRres[i])])
    rank = np.array(rank)
    rank = rank[rank[:, 1].argsort()[::-1]]
    print(rank)
    print("rank shape: ", rank.shape)
    RAUC(rank, bestAUC(rank))
    EXAM_F(rank)
    EXAM_L(rank)
    EXAM_AVG(rank)
    PoBL(rank, 0.1)
    APFD(rank)


def PROCESS(modeltype, datatype, ablation, dataratio, pattern):
    if dataratio == '005':
        dataratio = ''
    if dataratio == '':
        path = './retrainmodel/'
    else:
        path = 'F:/ICSEdata/model/'
    print(path)
    if modeltype == 'LSTM':
        orgmodel = LSTM(voc_len=len(vocab), PAD=vocab.PAD)
        S1model = LSTM(voc_len=len(vocab), PAD=vocab.PAD)
        S2model = LSTM(voc_len=len(vocab), PAD=vocab.PAD)
        S3model = LSTM(voc_len=len(vocab), PAD=vocab.PAD)

        orgstate_dict = torch.load('./models/agnews_' + datatype + '_LSTM.pth')
        orgmodel.load_state_dict(orgstate_dict)

        S1state_dict = torch.load(path + 'agnews_' + datatype + '_LSTM_retrain_VAE' + dataratio + '.pth')
        S1model.load_state_dict(S1state_dict)

        S2state_dict = torch.load('./retrainmodel/agnews_' + datatype + '_LSTM_retrain_Kmeans.pth')
        S2model.load_state_dict(S2state_dict)

        S3state_dict = torch.load(path + 'agnews_' + datatype + '_LSTM_retrain_LOSS' + dataratio + '.pth')
        S3model.load_state_dict(S3state_dict)
    elif modeltype == 'BiLSTM':
        orgmodel = BiLSTM(voc_len=len(vocab), PAD=vocab.PAD)
        S1model = BiLSTM(voc_len=len(vocab), PAD=vocab.PAD)
        S2model = BiLSTM(voc_len=len(vocab), PAD=vocab.PAD)
        S3model = BiLSTM(voc_len=len(vocab), PAD=vocab.PAD)

        orgstate_dict = torch.load('./models/agnews_' + datatype + '_BiLSTM.pth')
        orgmodel.load_state_dict(orgstate_dict)

        S1state_dict = torch.load(path + 'agnews_' + datatype + '_BiLSTM_retrain_VAE' + dataratio + '.pth')
        S1model.load_state_dict(S1state_dict)

        S2state_dict = torch.load('./retrainmodel/agnews_' + datatype + '_BiLSTM_retrain_Kmeans.pth')
        S2model.load_state_dict(S2state_dict)

        S3state_dict = torch.load(path + 'agnews_' + datatype + '_BILSTM_retrain_LOSS' + dataratio + '.pth')
        S3model.load_state_dict(S3state_dict)

    if dataratio == '':
        DP = './data/AgNews/AgNews_NEWDATA_Out/'
    else:
        DP = 'F:/ICSEdata/data/AgNews/'
    print(DP)

    datapath = DP + datatype + 'traindata_VAE_Kmeans_LOSS_' + modeltype + dataratio + '.npy'

    predata = np.load(datapath, allow_pickle=True)
    y_train = torch.from_numpy(np.array([int(x) for x in predata[:, 0]]))
    is_dirty = torch.from_numpy(np.array([int(x) for x in predata[:, 2]]))
    orgmodel.eval()
    S1model.eval()
    S2model.eval()
    S3model.eval()
    if pattern == 'getfeature':
        orgsfm, orgloss = getOUTPUT(orgmodel, datapath)
        print('org shape:', orgsfm.shape, orgloss.shape)

        GTsfm = getGT(datapath)
        print('GTsfm shape:', GTsfm.shape)

        S1sfm, S1loss = getOUTPUT(S1model, datapath)
        print('S1 shape:', S1sfm.shape, S1loss.shape)

        S2sfm, S2loss = getOUTPUT(S2model, datapath)
        print('S2 shape:', S2sfm.shape, S2loss.shape)

        S3sfm, S3loss = getOUTPUT(S3model, datapath)
        print('S3 shape:', S3sfm.shape, S3loss.shape)

        suslist = S1loss + S2loss + S3loss - orgloss

        get_featureV(datapath, orgsfm, GTsfm, S1sfm, S2sfm, S3sfm, orgloss, S1loss, S2loss, S3loss, suslist, datatype,
                     modeltype, dataratio)
    # #
    elif pattern == 'AT':
        if dataratio == '':
            FP = './data/AgNews/AgNews_LR_feature/'
            DR = 'new'
        else:
            FP = 'F:/ICSEdata/feature/'
            DR = dataratio
        print(FP)

        feaVec = np.load(FP + DR + '_' + datatype + '_feature_' + modeltype + '.npy')
        print(feaVec.shape)
        if ablation == 'input':
            de = [x for x in range(12, 20)]
            de.append(21)
            de.append(22)
            de.append(25)
            de.append(26)
            feaVec = np.delete(feaVec, de, axis=1)
        elif ablation == 'hidden':
            de = [x for x in range(8, 12)]
            for i in range(16, 20):
                de.append(i)
            de.append(20)
            de.append(22)
            de.append(24)
            de.append(26)
            feaVec = np.delete(feaVec, de, axis=1)
        elif ablation == 'output':
            de = [x for x in range(8, 16)]
            de.append(20)
            de.append(21)
            de.append(24)
            de.append(25)
            feaVec = np.delete(feaVec, de, axis=1)
        elif ablation == 'input+hidden':
            de = [x for x in range(16, 20)]
            de.append(22)
            de.append(26)
            feaVec = np.delete(feaVec, de, axis=1)
        elif ablation == 'hidden+output':
            de = [x for x in range(8, 12)]
            de.append(20)
            de.append(24)
            feaVec = np.delete(feaVec, de, axis=1)
        elif ablation == 'input+output':
            de = [x for x in range(12, 26)]
            de.append(21)
            de.append(25)
            feaVec = np.delete(feaVec, de, axis=1)

        print(feaVec.shape)
        # UPDATE(feaVec, modeltype, datatype, is_dirty)
        return AT(feaVec, modeltype, datatype, is_dirty, ablation)
    return

    get_susp_rank_res(feaVec[:, -2], is_dirty)

    num = 200

    feaVec = feaVec[feaVec[:, -2].argsort()[::-1]]

    X = np.vstack((feaVec[0:num, 0:-1], feaVec[-num:120000, 0:-1]))  ####@@@@

    Y = np.concatenate((feaVec[0:num, -1], feaVec[-num:120000, -1]))

    print(X.shape, Y.shape)

    lg = LogisticRegression(C=1.0)
    lg.fit(X, Y)

    LRres = lg.predict_proba(feaVec[0:120000, 0:-1])  ####@@@@
    LRres = LRres[:, 1]

    rank = []
    for i in range(is_dirty.shape[0]):
        rank.append([int(feaVec[i][-1]), float(LRres[i])])

    rank = np.array(rank)
    rank = rank[rank[:, 1].argsort()[::-1]]
    print(rank)
    print("rank shape: ", rank.shape)
    RAUC(rank, bestAUC(rank))
    EXAM_F(rank)
    EXAM_L(rank)
    EXAM_AVG(rank)
    PoBL(rank, 0.1)
    APFD(rank)


from scipy.stats import ranksums
from cliffs_delta import cliffs_delta


def check(a, b):
    ans = ''
    s, p = ranksums(a, b)
    d, res = cliffs_delta(a, b)
    if p >= 0.05:
        ans = 'T'
    elif p < 0.05:
        if d >= 0.147:
            ans = 'W'
        elif d <= -0.147:
            ans = 'L'
        else:
            ans = 'T'
    return ans


def writexcel(sheet, x, P, val, color, offset):
    style1 = "font:colour_index red;"
    style2 = "font:colour_index blue;"
    style3 = "font:colour_index green;"
    style4 = "font:colour_index black;"
    if color == 'W':
        style = xlwt.easyxf(style1)
    elif color == 'T':
        style = xlwt.easyxf(style2)
    elif color == 'L':
        style = xlwt.easyxf(style3)
    else:
        style = xlwt.easyxf(style4)
    y = -1
    if P == 'input':
        y = 0
    elif P == 'hidden':
        y = 1
    elif P == 'output':
        y = 2
    elif P == 'input+hidden':
        y = 3

    elif P == 'hidden+output':
        y = 4
    elif P == 'input+output':
        y = 5
    elif P == 'all':
        y = 6
    else:
        y = P
    sheet.write(x, y + offset, val, style)


def RQ2_1():
    # args:
    dtlist = ['alllabel', 'ranlabel', 'alldirty', 'randirty']
    datasetname = 'AgNews'
    mdlist = ['LSTM', 'BiLSTM']
    ablist = ['input', 'hidden', 'output', 'input+hidden', 'hidden+output', 'input+output', 'all']

    # res[datatype][dataratio][modeltype][args]
    res = [[[[[] for g in range(6)] for k in range(len(mdlist))] for j in range(len(ablist))] for i in
           range(len(dtlist))]

    workbook = xlwt.Workbook()  # 新建一个工作簿
    sheet = workbook.add_sheet('1')  # 在工作簿中新建一个表格

    for DATATYPE in dtlist:
        for ablation in ablist:
            for MODELTYPE in mdlist:
                random.seed(6657)
                for _ in range(PALL):
                    print('now run:' + DATATYPE + ' ' + ablation + ' ' + MODELTYPE + ' ' + str(_ + 1) + '/' + str(PALL))
                    t1, t2, t3, f, l, avg = PROCESS(modeltype=MODELTYPE, datatype=DATATYPE, ablation=ablation,
                                                           dataratio='', pattern='AT')
                    res[dtlist.index(DATATYPE)][ablist.index(ablation)][mdlist.index(MODELTYPE)][0].append(t1)
                    res[dtlist.index(DATATYPE)][ablist.index(ablation)][mdlist.index(MODELTYPE)][1].append(t2)
                    res[dtlist.index(DATATYPE)][ablist.index(ablation)][mdlist.index(MODELTYPE)][2].append(t3)
                    res[dtlist.index(DATATYPE)][ablist.index(ablation)][mdlist.index(MODELTYPE)][3].append(f)
                    res[dtlist.index(DATATYPE)][ablist.index(ablation)][mdlist.index(MODELTYPE)][4].append(l)
                    res[dtlist.index(DATATYPE)][ablist.index(ablation)][mdlist.index(MODELTYPE)][5].append(avg)

        for MODELTYPE in mdlist:
            ORG = res[dtlist.index(DATATYPE)][ablist.index('all')][mdlist.index(MODELTYPE)]
            file = open('save.txt', 'a')
            s1 = format(sum(ORG[0]) / len(ORG[0]), '.4f')
            s2 = format(sum(ORG[1]) / len(ORG[1]), '.4f')
            s3 = format(sum(ORG[2]) / len(ORG[2]), '.4f')
            file.write(MODELTYPE + ' ' + DATATYPE + ' ' + 'all: ' + str(s1) + ' '
                       + str(s2) + ' ' + str(s3) + '\n')
            file.close()
            writexcel(sheet, mdlist.index(MODELTYPE) * len(dtlist) + dtlist.index(DATATYPE), 6, s1, '', 0)
            writexcel(sheet, mdlist.index(MODELTYPE) * len(dtlist) + dtlist.index(DATATYPE), 6, s2, '', 8)
            writexcel(sheet, mdlist.index(MODELTYPE) * len(dtlist) + dtlist.index(DATATYPE), 6, s3, '', 16)
            for ablation in ablist:
                if ablation == 'all':
                    continue
                SPC = res[dtlist.index(DATATYPE)][ablist.index(ablation)][mdlist.index(MODELTYPE)]
                PoBL_WTL = check(ORG[0], SPC[0])
                APFD_WTL = check(ORG[1], SPC[1])
                RAUC_WTL = check(ORG[2], SPC[2])
                s1 = format(sum(SPC[0]) / len(SPC[0]), '.4f')
                s2 = format(sum(SPC[1]) / len(SPC[1]), '.4f')
                s3 = format(sum(SPC[2]) / len(SPC[2]), '.4f')

                file = open('save.txt', 'a')
                file.write(MODELTYPE + ' ' + DATATYPE + ' ' + ablation + ': ' + str(s1) + ' '
                           + str(s2) + ' ' + str(s3) + ' ' + PoBL_WTL + ' ' + APFD_WTL + ' ' + RAUC_WTL + '\n')
                file.close()
                writexcel(sheet, mdlist.index(MODELTYPE) * len(dtlist) + dtlist.index(DATATYPE),
                          ablist.index(ablation), s1, PoBL_WTL, 0)
                writexcel(sheet, mdlist.index(MODELTYPE) * len(dtlist) + dtlist.index(DATATYPE),
                          ablist.index(ablation), s2, APFD_WTL, 8)
                writexcel(sheet, mdlist.index(MODELTYPE) * len(dtlist) + dtlist.index(DATATYPE),
                          ablist.index(ablation), s3, RAUC_WTL, 16)

    workbook.save('F:/ICSEdata/excel/' + datasetname + '_RQ2_1.xls')
    res = np.array(res)
    np.save('F:/ICSEdata/RQdata/' + datasetname + '_RQ2_1.npy', res)


PALL = 10


def PROCESS_randomweight(modeltype, datatype, ablation):
    if modeltype == 'LSTM':
        orgmodel = LSTM(voc_len=len(vocab), PAD=vocab.PAD)
        S1model = getlockmodelLSTM('./models/agnews_' + datatype + '_LSTM.pth')
        S2model = getlockmodelLSTM('./models/agnews_' + datatype + '_LSTM.pth')
        S3model = getlockmodelLSTM('./models/agnews_' + datatype + '_LSTM.pth')

        orgstate_dict = torch.load('./models/agnews_' + datatype + '_LSTM.pth')
        orgmodel.load_state_dict(orgstate_dict)

        S1state_dict = torch.load('./retrainmodel/agnews_' + datatype + '_LSTM_retrain_VAE_randomweight.pth')
        S1model.load_state_dict(S1state_dict)

        S2state_dict = torch.load('./retrainmodel/agnews_' + datatype + '_LSTM_retrain_Kmeans_randomweight.pth')
        S2model.load_state_dict(S2state_dict)

        S3state_dict = torch.load('./retrainmodel/agnews_' + datatype + '_LSTM_retrain_LOSS_randomweight.pth')
        S3model.load_state_dict(S3state_dict)

    elif modeltype == 'BiLSTM':
        orgmodel = BiLSTM(voc_len=len(vocab), PAD=vocab.PAD)
        S1model = getlockmodelBiLSTM('./models/agnews_' + datatype + '_BiLSTM.pth')
        S2model = getlockmodelBiLSTM('./models/agnews_' + datatype + '_BiLSTM.pth')
        S3model = getlockmodelBiLSTM('./models/agnews_' + datatype + '_BiLSTM.pth')

        orgstate_dict = torch.load('./models/agnews_' + datatype + '_BiLSTM.pth')
        orgmodel.load_state_dict(orgstate_dict)

        S1state_dict = torch.load('./retrainmodel/agnews_' + datatype + '_BiLSTM_retrain_VAE_randomweight.pth')
        S1model.load_state_dict(S1state_dict)

        S2state_dict = torch.load('./retrainmodel/agnews_' + datatype + '_BiLSTM_retrain_Kmeans_randomweight.pth')
        S2model.load_state_dict(S2state_dict)

        S3state_dict = torch.load('./retrainmodel/agnews_' + datatype + '_BiLSTM_retrain_LOSS_randomweight.pth')
        S3model.load_state_dict(S3state_dict)
    datapath = './data/AgNews/AgNews_NEWDATA_Out/' + datatype + 'traindata_VAE_Kmeans_LOSS_' + modeltype + '.npy'

    predata = np.load(datapath, allow_pickle=True)
    y_train = torch.from_numpy(np.array([int(x) for x in predata[:, 0]]))
    is_dirty = torch.from_numpy(np.array([int(x) for x in predata[:, 2]]))
    orgmodel.eval()
    S1model.eval()
    S2model.eval()
    S3model.eval()
    # orgsfm, orgloss = getOUTPUT(orgmodel, datapath)
    # print('org shape:', orgsfm.shape, orgloss.shape)
    #
    #
    # GTsfm = getGT(datapath)
    # print('GTsfm shape:', GTsfm.shape)
    #
    #
    # S1sfm,S1loss = getOUTPUT(S1model, datapath)
    # print('S1 shape:', S1sfm.shape,S1loss.shape)
    #
    # S2sfm,S2loss= getOUTPUT(S2model, datapath)
    # print('S2 shape:', S2sfm.shape,S2loss.shape)
    #
    # S3sfm ,S3loss= getOUTPUT(S3model, datapath)
    # print('S3 shape:', S3sfm.shape,S3loss.shape)
    #
    # suslist=S1loss+S2loss+S3loss-orgloss
    #
    # get_featureV(datapath,orgsfm,GTsfm,S1sfm,S2sfm,S3sfm,orgloss,S1loss,S2loss,S3loss,suslist,datatype,modeltype)
    #
    feaVec = np.load('./data/AgNews/AgNews_LR_feature/' + 'randomweight_' + datatype + '_feature_' + modeltype + '.npy')
    print(feaVec.shape)
    if ablation == 'input':
        de = [x for x in range(12, 20)]
        de.append(21)
        de.append(22)
        de.append(25)
        de.append(26)
        feaVec = np.delete(feaVec, de, axis=1)
    elif ablation == 'hidden':
        de = [x for x in range(8, 12)]
        for i in range(16, 20):
            de.append(i)
        de.append(20)
        de.append(22)
        de.append(24)
        de.append(26)
        feaVec = np.delete(feaVec, de, axis=1)
    elif ablation == 'output':
        de = [x for x in range(8, 16)]
        de.append(20)
        de.append(21)
        de.append(24)
        de.append(25)
        feaVec = np.delete(feaVec, de, axis=1)
    elif ablation == 'input+hidden':
        de = [x for x in range(16, 20)]
        de.append(22)
        de.append(26)
        feaVec = np.delete(feaVec, de, axis=1)
    elif ablation == 'hidden+output':
        de = [x for x in range(8, 12)]
        de.append(20)
        de.append(24)
        feaVec = np.delete(feaVec, de, axis=1)
    elif ablation == 'input+output':
        de = [x for x in range(12, 26)]
        de.append(21)
        de.append(25)
        feaVec = np.delete(feaVec, de, axis=1)

    print(feaVec.shape)
    # UPDATE(feaVec, modeltype, datatype, is_dirty)
    return AT(feaVec, modeltype, datatype, is_dirty, ablation)


def RQ2_2():
    dtlist = ['alllabel', 'ranlabel', 'alldirty', 'randirty']

    # args:
    MODELTYPE = 'BiLSTM'

    row = -1
    workbook = xlwt.Workbook()  # 新建一个工作簿
    sheet = workbook.add_sheet('1')  # 在工作簿中新建一个表格
    # for i in range(PALL):

    for DATATYPE in dtlist:
        row += 1

        save_RT = [0, 0, 0, 0, 0, 0]
        save_DT = [0, 0, 0, 0, 0, 0]

        PoBL_RT = []
        APFD_RT = []
        RAUC_RT = []

        PoBL_DT = []
        APFD_DT = []
        RAUC_DT = []
        random.seed(6657)
        for _ in range(PALL):
            print('now run:' + 'direct' + ' ' + DATATYPE + ' ' + str(_) + '/' + str(PALL))
            t1, t2, t3, f, l, avg = PROCESS(modeltype=MODELTYPE, datatype=DATATYPE, ablation='all')
            PoBL_DT.append(t1)
            APFD_DT.append(t2)
            RAUC_DT.append(t3)
            save_DT[0] += t1
            save_DT[1] += t2
            save_DT[2] += t3
            save_DT[3] += f
            save_DT[4] += l
            save_DT[5] += avg
        for i in range(6):
            save_DT[i] = save_DT[i] / PALL

        random.seed(6657)
        for _ in range(PALL):
            print('now run:' + 'randomweight' + ' ' + DATATYPE + ' ' + str(_) + '/' + str(PALL))
            t1, t2, t3, f, l, avg = PROCESS_randomweight(modeltype=MODELTYPE, datatype=DATATYPE, ablation='all')
            PoBL_RT.append(t1)
            APFD_RT.append(t2)
            RAUC_RT.append(t3)
            save_RT[0] += t1
            save_RT[1] += t2
            save_RT[2] += t3
            save_RT[3] += f
            save_RT[4] += l
            save_RT[5] += avg
        for i in range(6):
            save_RT[i] = save_RT[i] / PALL

        for i in range(6):
            save_RT[i] = format(save_RT[i], '.4f')
            save_DT[i] = format(save_DT[i], '.4f')

        PoBL_WTL = check(PoBL_DT, PoBL_RT)
        APFD_WTL = check(APFD_DT, APFD_RT)
        RAUC_WTL = check(RAUC_DT, RAUC_RT)

        file = open('save.txt', 'a')
        s1 = MODELTYPE + ' ' + DATATYPE + ' ' + 'direct' + ': ' + str(save_DT[0]) + ' ' + str(save_DT[1]) + ' ' + str(
            save_DT[2]) \
             + ' ' + str(save_DT[3]) + ' ' + str(save_DT[4]) + ' ' + str(
            save_DT[5]) + '\n'
        s2 = MODELTYPE + ' ' + DATATYPE + ' ' + 'randomweight' + ': ' + str(save_RT[0]) + ' ' + str(
            save_RT[1]) + ' ' + str(
            save_RT[2]) \
             + ' ' + str(save_RT[3]) + ' ' + str(save_RT[4]) + ' ' + str(
            save_RT[5]) + ' ' + PoBL_WTL + ' ' + APFD_WTL + ' ' + RAUC_WTL + '\n'
        file.write(s1)
        file.write(s2)
        file.close()

        writexcel(sheet, row, 5, save_DT[0], '', 0)
        writexcel(sheet, row, 5, save_DT[1], '', 6)
        writexcel(sheet, row, 5, save_DT[2], '', 12)

        writexcel(sheet, row, 4, save_RT[0], PoBL_WTL, 0)
        writexcel(sheet, row, 4, save_RT[1], APFD_WTL, 6)
        writexcel(sheet, row, 4, save_RT[2], RAUC_WTL, 12)
    workbook.save('C:/Users/WSHdeWindows/Desktop/res.xls')


def RQ2_3():
    dtlist = ['alllabel', 'ranlabel', 'alldirty', 'randirty']

    # args:
    datasetname = 'AgNews'
    mdlist = ['LSTM', 'BiLSTM']
    ralist = ['003', '005', '010', '020']

    # res[datatype][dataratio][modeltype][args]
    res = [[[[[] for g in range(6)] for k in range(len(mdlist))] for j in range(len(ralist))] for i in
           range(len(dtlist))]

    row = -1
    workbook = xlwt.Workbook()  # 新建一个工作簿
    sheet = workbook.add_sheet('1')  # 在工作簿中新建一个表格
    # for i in range(PALL):

    for DATATYPE in dtlist:
        for dataratio in ralist:
            for MODELTYPE in mdlist:
                random.seed(6657)
                for _ in range(PALL):
                    print('now run:' + DATATYPE + ' ' + dataratio + ' ' + MODELTYPE + str(_ + 1) + '/' + str(PALL))
                    t1, t2, t3, f, l, avg = PROCESS(modeltype=MODELTYPE, datatype=DATATYPE, ablation='all',
                                                    dataratio=dataratio, pattern='AT')
                    res[dtlist.index(DATATYPE)][ralist.index(dataratio)][mdlist.index(MODELTYPE)][0].append(t1)
                    res[dtlist.index(DATATYPE)][ralist.index(dataratio)][mdlist.index(MODELTYPE)][1].append(t2)
                    res[dtlist.index(DATATYPE)][ralist.index(dataratio)][mdlist.index(MODELTYPE)][2].append(t3)
                    res[dtlist.index(DATATYPE)][ralist.index(dataratio)][mdlist.index(MODELTYPE)][3].append(f)
                    res[dtlist.index(DATATYPE)][ralist.index(dataratio)][mdlist.index(MODELTYPE)][4].append(l)
                    res[dtlist.index(DATATYPE)][ralist.index(dataratio)][mdlist.index(MODELTYPE)][5].append(avg)

        for MODELTYPE in mdlist:
            ORG = res[dtlist.index(DATATYPE)][ralist.index('005')][mdlist.index(MODELTYPE)]
            file = open('save.txt', 'a')
            s1 = format(sum(ORG[0]) / len(ORG[0]), '.4f')
            s2 = format(sum(ORG[1]) / len(ORG[1]), '.4f')
            s3 = format(sum(ORG[2]) / len(ORG[2]), '.4f')
            file.write(MODELTYPE + ' ' + DATATYPE + ' ' + '005: ' + str(s1) + ' '
                       + str(s2) + ' ' + str(s3) + '\n')
            file.close()
            writexcel(sheet, mdlist.index(MODELTYPE) * len(dtlist) + dtlist.index(DATATYPE), 1, s1, '', 0)
            writexcel(sheet, mdlist.index(MODELTYPE) * len(dtlist) + dtlist.index(DATATYPE), 1, s2, '', 6)
            writexcel(sheet, mdlist.index(MODELTYPE) * len(dtlist) + dtlist.index(DATATYPE), 1, s3, '', 12)
            for dataratio in ralist:
                if dataratio=='005':
                    continue
                SPC = res[dtlist.index(DATATYPE)][ralist.index(dataratio)][mdlist.index(MODELTYPE)]
                PoBL_WTL = check(ORG[0], SPC[0])
                APFD_WTL = check(ORG[1], SPC[1])
                RAUC_WTL = check(ORG[2], SPC[2])
                s1 = format(sum(SPC[0]) / len(SPC[0]), '.4f')
                s2 = format(sum(SPC[1]) / len(SPC[1]), '.4f')
                s3 = format(sum(SPC[2]) / len(SPC[2]), '.4f')

                file = open('save.txt', 'a')
                file.write(MODELTYPE + ' ' + DATATYPE + ' ' + dataratio + ': '+str(s1) + ' '
                           + str(s2) + ' ' + str(s3) + ' ' + PoBL_WTL + ' ' + APFD_WTL + ' ' + RAUC_WTL + '\n')
                file.close()
                writexcel(sheet, mdlist.index(MODELTYPE) * len(dtlist) + dtlist.index(DATATYPE),
                          ralist.index(dataratio), s1, PoBL_WTL, 0)
                writexcel(sheet, mdlist.index(MODELTYPE) * len(dtlist) + dtlist.index(DATATYPE),
                          ralist.index(dataratio), s2, APFD_WTL, 6)
                writexcel(sheet, mdlist.index(MODELTYPE) * len(dtlist) + dtlist.index(DATATYPE),
                          ralist.index(dataratio), s3, RAUC_WTL, 12)

    workbook.save('F:/ICSEdata/excel/' + datasetname + '_RQ2_2.xls')
    res = np.array(res)
    np.save('F:/ICSEdata/RQdata/' + datasetname + '_RQ2_2.npy', res)
    #     row += 1
    #
    #     save_RT = [0, 0, 0, 0, 0, 0]
    #     save_DT = [0, 0, 0, 0, 0, 0]
    #
    #     PoBL_RT = []
    #     APFD_RT = []
    #     RAUC_RT = []
    #
    #     PoBL_DT = []
    #     APFD_DT = []
    #     RAUC_DT = []
    #     random.seed(6657)
    #     for _ in range(PALL):
    #         print('now run:' + dataratio + ' ' + DATATYPE + ' ' + str(_) + '/' + str(PALL))
    #         t1, t2, t3, f, l, avg = PROCESS(modeltype=MODELTYPE, datatype=DATATYPE, ablation='all',
    #                                         dataratio=dataratio, pattern='AT')
    #         PoBL_RT.append(t1)
    #         APFD_RT.append(t2)
    #         RAUC_RT.append(t3)
    #         save_RT[0] += t1
    #         save_RT[1] += t2
    #         save_RT[2] += t3
    #         save_RT[3] += f
    #         save_RT[4] += l
    #         save_RT[5] += avg
    #     for i in range(6):
    #         save_RT[i] = save_RT[i] / PALL
    #
    #     random.seed(6657)
    #     for _ in range(PALL):
    #         print('now run:' + 'direct' + ' ' + DATATYPE + ' ' + str(_) + '/' + str(PALL))
    #         t1, t2, t3, f, l, avg = PROCESS(modeltype=MODELTYPE, datatype=DATATYPE, ablation='all',
    #                                         dataratio='', pattern='AT')
    #         PoBL_DT.append(t1)
    #         APFD_DT.append(t2)
    #         RAUC_DT.append(t3)
    #         save_DT[0] += t1
    #         save_DT[1] += t2
    #         save_DT[2] += t3
    #         save_DT[3] += f
    #         save_DT[4] += l
    #         save_DT[5] += avg
    #     for i in range(6):
    #         save_DT[i] = save_DT[i] / PALL
    #
    #     for i in range(6):
    #         save_RT[i] = format(save_RT[i], '.4f')
    #         save_DT[i] = format(save_DT[i], '.4f')
    #
    #     PoBL_WTL = check(PoBL_DT, PoBL_RT)
    #     APFD_WTL = check(APFD_DT, APFD_RT)
    #     RAUC_WTL = check(RAUC_DT, RAUC_RT)
    #
    #     file = open('save.txt', 'a')
    #     s1 = MODELTYPE + ' ' + DATATYPE + ' ' + 'direct' + ': ' + str(save_DT[0]) + ' ' + str(save_DT[1]) + ' ' + str(
    #         save_DT[2]) \
    #          + ' ' + str(save_DT[3]) + ' ' + str(save_DT[4]) + ' ' + str(
    #         save_DT[5]) + '\n'
    #     s2 = MODELTYPE + ' ' + DATATYPE + ' ' + dataratio + ': ' + str(save_RT[0]) + ' ' + str(
    #         save_RT[1]) + ' ' + str(
    #         save_RT[2]) \
    #          + ' ' + str(save_RT[3]) + ' ' + str(save_RT[4]) + ' ' + str(
    #         save_RT[5]) + ' ' + PoBL_WTL + ' ' + APFD_WTL + ' ' + RAUC_WTL + '\n'
    #     file.write(s1)
    #     file.write(s2)
    #     file.close()
    #
    #     # writexcel(sheet, row, 5, save_DT[0], '', 0)
    #     # writexcel(sheet, row, 5, save_DT[1], '', 6)
    #     # writexcel(sheet, row, 5, save_DT[2], '', 12)
    #
    #     writexcel(sheet, row, 0, save_RT[0], PoBL_WTL, 0)
    #     writexcel(sheet, row, 0, save_RT[1], APFD_WTL, 6)
    #     writexcel(sheet, row, 0, save_RT[2], RAUC_WTL, 12)
    # workbook.save('C:/Users/WSHdeWindows/Desktop/res.xls')


if __name__ == "__main__":
    RQ2_1()
    # S3model = BiLSTM(voc_len=len(vocab), PAD=vocab.PAD)
    # S3state_dict = torch.load('./retrainmodel/agnews_alllabel_BiLSTM_retrain_LOSS.pth')
    # S3model.load_state_dict(S3state_dict)
    # RQ2_1()
    # PROCESS_randomweight(modeltype='BiLSTM', datatype='randirty',ablation='all')

    # dtlist = ['alllabel', 'ranlabel', 'alldirty', 'randirty']
    # mdlist = ['LSTM', 'BiLSTM']
    # dellist = ['003', '010', '020']
    # for dataratio in dellist:
    #     for modeltype in mdlist:
    #         for datatype in dtlist:
    #             print('now run:' + dataratio + ' ' + modeltype + ' ' + datatype)
    #             PROCESS(modeltype=modeltype, datatype=datatype, ablation='all', dataratio=dataratio, pattern='getfeature')