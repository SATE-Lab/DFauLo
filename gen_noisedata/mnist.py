import os
import random

import cv2
import numpy as np
import argparse


parser = argparse.ArgumentParser()



parser.add_argument('--datapath', type=str, default='', help='input data path.')
parser.add_argument('--savepath', type=str, default='', help='save data path.')
parser.add_argument('--datatype', type=str, default='original', help='datatype to generate which includes original or '
                                                                     'RandomLabelNoise or SpecificLabelNoise'
                                                                     'RandomDataNoise or SpecificDataNoise '
                                                                     'you shall generate original data first.')


args = parser.parse_args()


def load_orgdata(datapth, savepath):
    traindata = []
    for label in os.listdir(datapth + 'train'):
        for imgname in os.listdir(datapth + 'train/' + str(label)):
            imgpath = datapth + 'train/' + str(label) + '/' + imgname
            img = cv2.imread(imgpath)
            img = np.array(img, dtype=np.float32)
            traindata.append([label, img, 0])
    traindata = np.array(traindata, dtype=object)
    print("train data shape: ", traindata.shape)
    np.save(savepath + 'orgtraindata', traindata)

    testdata = []
    for label in os.listdir(datapth + 'test'):
        for imgname in os.listdir(datapth + 'test/' + str(label)):
            imgpath = datapth + 'test/' + str(label) + '/' + imgname
            img = cv2.imread(imgpath)
            img = np.array(img, dtype=np.float32)
            testdata.append([label, img, 0])
    testdata = np.array(testdata, dtype=object)
    print("test data shape: ", testdata.shape)
    np.save(savepath + 'orgtestdata', testdata)


def load_alldirtydata(datapth, savepath, ratio):
    traindata = []
    trainNumAll = [5923, 6742, 5958, 6131, 5842, 5421, 5918, 6265, 5851, 5949]
    testNumAll = [980, 1135, 1032, 1010, 982, 892, 958, 1028, 974, 1009]
    for label in os.listdir(datapth + 'train'):
        cnt = 0
        for imgname in os.listdir(datapth + 'train/' + str(label)):
            if cnt < trainNumAll[int(label)] * ratio:
                newimg_path = "./data/CIFA10/CIFA10_PNG/train/"
                p = random.randint(0, 9)
                newimg_path = newimg_path + str(p)
                list = []
                for x in os.listdir(newimg_path):
                    list.append(x)
                imagename = random.sample(list, 1)
                newimg = cv2.imread(newimg_path + "/" + str(imagename[0]))
                newimg = cv2.resize(newimg, (28, 28), interpolation=cv2.INTER_CUBIC)
                img = np.array(newimg, dtype=np.float32)
                traindata.append([label, img, 1])
                cnt += 1
            else:
                imgpath = datapth + 'train/' + str(label) + '/' + imgname
                img = cv2.imread(imgpath)
                img = np.array(img, dtype=np.float32)
                traindata.append([label, img, 0])

    traindata = np.array(traindata, dtype=object)
    print("train data shape: ", traindata.shape)
    np.save(savepath + 'alldirtytraindata', traindata)

    testdata = []
    for label in os.listdir(datapth + 'test'):
        cnt = 0
        for imgname in os.listdir(datapth + 'test/' + str(label)):
            if cnt < testNumAll[int(label)] * ratio:
                newimg_path = "./data/CIFA10/CIFA10_PNG/train/"
                p = random.randint(0, 9)
                newimg_path = newimg_path + str(p)
                list = []
                for x in os.listdir(newimg_path):
                    list.append(x)
                imagename = random.sample(list, 1)
                newimg = cv2.imread(newimg_path + "/" + str(imagename[0]))
                newimg = cv2.resize(newimg, (28, 28), interpolation=cv2.INTER_CUBIC)
                img = np.array(newimg, dtype=np.float32)
                testdata.append([label, img, 1])
                cnt += 1
            else:
                imgpath = datapth + 'test/' + str(label) + '/' + imgname
                img = cv2.imread(imgpath)
                img = np.array(img, dtype=np.float32)
                testdata.append([label, img, 0])
    testdata = np.array(testdata, dtype=object)
    print("test data shape: ", testdata.shape)
    np.save(savepath + 'alldirtytestdata', testdata)


def load_randirtydata(datapth, savepath, ratio):
    traindata = []
    trainNumAll = [5923, 6742, 5958, 6131, 5842, 5421, 5918, 6265, 5851, 5949]
    testNumAll = [980, 1135, 1032, 1010, 982, 892, 958, 1028, 974, 1009]
    dirtylabel = random.randint(0, 9)
    print("dirty label: ", dirtylabel)
    cnt = 0
    for label in os.listdir(datapth + 'train'):
        for imgname in os.listdir(datapth + 'train/' + str(label)):
            if int(dirtylabel) == int(label) and cnt < trainNumAll[int(label)] * ratio:
                newimg_path = "./data/CIFA10/CIFA10_PNG/train/"
                p = random.randint(0, 9)
                newimg_path = newimg_path + str(p)
                list = []
                for x in os.listdir(newimg_path):
                    list.append(x)
                imagename = random.sample(list, 1)
                newimg = cv2.imread(newimg_path + "/" + str(imagename[0]))
                newimg = cv2.resize(newimg, (28, 28), interpolation=cv2.INTER_CUBIC)
                img = np.array(newimg, dtype=np.float32)
                traindata.append([label, img, 1])
                cnt += 1
            else:
                imgpath = datapth + 'train/' + str(label) + '/' + imgname
                img = cv2.imread(imgpath)
                img = np.array(img, dtype=np.float32)
                traindata.append([label, img, 0])
    print(cnt)
    traindata = np.array(traindata, dtype=object)
    print("train data shape: ", traindata.shape)
    np.save(savepath + 'randirtytraindata', traindata)

    testdata = []
    cnt = 0
    for label in os.listdir(datapth + 'test'):
        for imgname in os.listdir(datapth + 'test/' + str(label)):
            if int(dirtylabel) == int(label) and cnt < testNumAll[int(label)] * ratio:
                newimg_path = "./data/CIFA10/CIFA10_PNG/train/"
                p = random.randint(0, 9)
                newimg_path = newimg_path + str(p)
                list = []
                for x in os.listdir(newimg_path):
                    list.append(x)
                imagename = random.sample(list, 1)
                newimg = cv2.imread(newimg_path + "/" + str(imagename[0]))
                newimg = cv2.resize(newimg, (28, 28), interpolation=cv2.INTER_CUBIC)
                img = np.array(newimg, dtype=np.float32)
                testdata.append([label, img, 1])
                cnt += 1
            else:
                imgpath = datapth + 'test/' + str(label) + '/' + imgname
                img = cv2.imread(imgpath)
                img = np.array(img, dtype=np.float32)
                testdata.append([label, img, 0])
    print(cnt)
    testdata = np.array(testdata, dtype=object)
    print("test data shape: ", testdata.shape)
    np.save(savepath + 'randirtytestdata', testdata)


def load_ranlabeldata(datapth, savepath, ratio):
    traindata = []
    trainNumAll = [5923, 6742, 5958, 6131, 5842, 5421, 5918, 6265, 5851, 5949]
    testNumAll = [980, 1135, 1032, 1010, 982, 892, 958, 1028, 974, 1009]
    swl = random.sample(range(10), 2)
    print("swap list: ", swl)
    cnt0 = 0
    cnt1 = 0
    for label in os.listdir(datapth + 'train'):
        for imgname in os.listdir(datapth + 'train/' + str(label)):
            if int(label) == swl[0] and cnt0 < trainNumAll[int(label)] * ratio:
                imgpath = datapth + 'train/' + str(label) + '/' + imgname
                img = cv2.imread(imgpath)
                img = np.array(img, dtype=np.float32)
                newlabel = swl[1]
                traindata.append([newlabel, img, 1])
                cnt0 += 1
            elif int(label) == swl[1] and cnt1 < trainNumAll[int(label)] * ratio:
                imgpath = datapth + 'train/' + str(label) + '/' + imgname
                img = cv2.imread(imgpath)
                img = np.array(img, dtype=np.float32)
                newlabel = swl[0]
                traindata.append([newlabel, img, 1])
                cnt1 += 1
            else:
                imgpath = datapth + 'train/' + str(label) + '/' + imgname
                img = cv2.imread(imgpath)
                img = np.array(img, dtype=np.float32)
                traindata.append([label, img, 0])
    print(cnt0,cnt1)
    traindata = np.array(traindata, dtype=object)
    print("train data shape: ", traindata.shape)
    np.save(savepath + 'ranlabeltraindata', traindata)

    testdata = []
    cnt0=0
    cnt1=0
    for label in os.listdir(datapth + 'test'):
        for imgname in os.listdir(datapth + 'test/' + str(label)):
            if int(label) == swl[0] and cnt0 < testNumAll[int(label)] * ratio:
                imgpath = datapth + 'test/' + str(label) + '/' + imgname
                img = cv2.imread(imgpath)
                img = np.array(img, dtype=np.float32)
                newlabel = swl[1]
                testdata.append([newlabel, img, 1])
                cnt0 += 1
            elif int(label) == swl[1] and cnt1 < testNumAll[int(label)] * ratio:
                imgpath = datapth + 'test/' + str(label) + '/' + imgname
                img = cv2.imread(imgpath)
                img = np.array(img, dtype=np.float32)
                newlabel = swl[0]
                testdata.append([newlabel, img, 1])
                cnt1 += 1

            else:
                imgpath = datapth + 'test/' + str(label) + '/' + imgname
                img = cv2.imread(imgpath)
                img = np.array(img, dtype=np.float32)
                testdata.append([label, img, 0])
    print(cnt0,cnt1)
    testdata = np.array(testdata, dtype=object)
    print("test data shape: ", testdata.shape)
    np.save(savepath + 'ranlabeltestdata', testdata)


def load_alllabeldata(datapth, savepath, ratio):
    traindata = []
    trainNumAll = [5923, 6742, 5958, 6131, 5842, 5421, 5918, 6265, 5851, 5949]
    testNumAll = [980, 1135, 1032, 1010, 982, 892, 958, 1028, 974, 1009]
    for label in os.listdir(datapth + 'train'):
        cnt = 0
        for imgname in os.listdir(datapth + 'train/' + str(label)):
            if cnt < trainNumAll[int(label)] * ratio:
                imgpath = datapth + 'train/' + str(label) + '/' + imgname
                img = cv2.imread(imgpath)
                img = np.array(img, dtype=np.float32)
                newlabel = random.randint(0, 9)
                while newlabel == int(label):
                    newlabel = random.randint(0, 9)
                traindata.append([newlabel, img, 1])
                cnt += 1
            else:
                imgpath = datapth + 'train/' + str(label) + '/' + imgname
                img = cv2.imread(imgpath)
                img = np.array(img, dtype=np.float32)
                traindata.append([label, img, 0])
        print(cnt)
    traindata = np.array(traindata, dtype=object)
    print("train data shape: ", traindata.shape)
    np.save(savepath + 'alllabeltraindata', traindata)

    testdata = []
    for label in os.listdir(datapth + 'test'):
        cnt = 0
        for imgname in os.listdir(datapth + 'test/' + str(label)):
            if cnt < testNumAll[int(label)] * ratio:
                imgpath = datapth + 'test/' + str(label) + '/' + imgname
                img = cv2.imread(imgpath)
                img = np.array(img, dtype=np.float32)
                newlabel = random.randint(0, 9)
                while newlabel == int(label):
                    newlabel = random.randint(0, 9)
                testdata.append([newlabel, img, 1])
                cnt += 1
            else:
                imgpath = datapth + 'test/' + str(label) + '/' + imgname
                img = cv2.imread(imgpath)
                img = np.array(img, dtype=np.float32)
                testdata.append([label, img, 0])
        print(cnt)
    testdata = np.array(testdata, dtype=object)
    print("test data shape: ", testdata.shape)
    np.save(savepath + 'alllabeltestdata', testdata)


if __name__ == "__main__":
    if args.datatype == 'original':
        load_orgdata(datapth=args.datapath,savepath=args.savepath)