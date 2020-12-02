# -*- coding: utf-8 -*-
"""covid-19_forecast_with_mlp.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1GQkG-LRUl7hXhnsdOPGg0qgSBQ1Tyu1P
"""

# Commented out IPython magic to ensure Python compatibility.
import os
# import datetime as dt#デフォはUTCの国際基準時間
# import pytz#日本時間に変換
import time
import warnings
warnings.simplefilter('ignore')
import sys
# from contextlib import redirect_stdout

import numpy as np
import pandas as pd
from pandas.plotting import register_matplotlib_converters
import matplotlib.pyplot as plt
# %matplotlib inline
import seaborn as sns
sns.set()

import statsmodels.api as sm # version 0.8.0以上
from sklearn.preprocessing import  MinMaxScaler
from sklearn.metrics import mean_absolute_error,mean_squared_error,mean_squared_error,r2_score

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Activation, Dropout, Flatten
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, LearningRateScheduler
from tensorflow.keras import regularizers
from tensorflow.keras.models import load_model
from tensorflow.keras import backend as K
from tensorflow.keras.utils import plot_model
from IPython.display import Image

# get args
args = sys.argv
ARG_NUM = 2
if(len(sys.argv) < ARG_NUM):
    print("Error")
    sys.exit(0)

# create df
df = pd.read_csv('COVID-19/time_series_covid19_confirmed_global.csv')
df = df[df['Country/Region']=='Japan']
df = df.iloc[:,4:].copy()
data_at_japan = df.iloc[0,:]
data_at_japan.index = pd.to_datetime(data_at_japan.index)
data_at_japan = data_at_japan['2020-01-22':'2020-10-28']

# plot fig and save
path = './log/original.png'
if not os.path.exists(path):
    plt.figure(figsize=(10,5))
    plt.plot(data_at_japan)
    plt.title('Cumulative confirmed cases in Japan', y = -0.2)
    plt.xlabel("Date")
    plt.ylabel("Confirmed cases (people)")
    plt.grid(True)
    plt.savefig(path)
    plt.close()
else:
  pass

res = sm.tsa.seasonal_decompose(data_at_japan, freq=7)#データを分解

original = data_at_japan # オリジナルデータ
trend_original = res.trend # トレンドデータ
seasonal_original = res.seasonal # 季節性データ
residual = res.resid # 残差データ

path ='log/decompose.png'
if not os.path.exists(path):
    plt.figure(figsize=(10, 20)) # グラフ描画枠作成、サイズ指定
    # オリジナルデータのプロット
    plt.subplot(411) # グラフ4行1列の1番目の位置（一番上）
    plt.plot(original)
    plt.title('Confirmed cases(Original) at Japan', y=-0.17)
    plt.xlabel("Date")
    plt.ylabel("Confirmed cases (people)")
    plt.grid(True)
    # trend データのプロット
    plt.subplot(412) # グラフ4行1列の2番目の位置
    plt.plot(trend_original)
    plt.title('Confirmed cases(Trend) at Japan', y=-0.17)
    plt.xlabel("Date")
    plt.ylabel("Confirmed cases (people)")
    plt.grid(True)
    # seasonalデータ のプロット
    plt.subplot(413) # グラフ4行1列の3番目の位置
    plt.plot(seasonal_original)
    plt.title('Confirmed cases(Seasonality) at Japan', y=-0.17)
    plt.xlabel("Date")
    plt.ylabel("Confirmed cases (people)")
    plt.grid(True)
    # residual データのプロット
    plt.subplot(414) # グラフ4行1列の4番目の位置（一番下）
    plt.plot(residual)
    plt.title('Confirmed cases(Residuals) at Japan', y=-0.17)
    plt.xlabel("Date")
    plt.ylabel("Confirmed cases (people)")
    plt.grid(True)
    plt.tight_layout() # グラフの間隔を自動調整
    plt.savefig(path)
    plt.close()
else:
    pass

y = data_at_japan.values.astype(float)
# print(len(y))

# train_test_split
test_size = 7
train_original_data = y[:-test_size]#0から後ろから4個目までを取り出す。　つまり学習用のデータ(学習の範囲)は直近３日間前
test_original_data = y[-test_size:]#最後から３つを取り出す。　検証用データは直近３日間前

# normalization
scaler = MinMaxScaler(feature_range=(-1,1))#feature_rangeは引数に正規化変換後の最大値と最小値を決める。今回は−１から１で正規化
train_normalized = scaler.fit_transform(train_original_data.reshape(-1,1))#学習用データに正規化の適用　またskleranの入力形状に適用 合わせた行と１列

# create datasets
def sequence_creator(input_data,window_size):#train_normalizedとwindow_sizeを渡し訓練データと正解ラベルを返す

    data, target = [], []
    data_len = len(input_data)
    for i in range(data_len - window_size):#data_lenのままだとwindowが配列を超えてしまう
        window_fr = input_data[i:i+window_size]#iを始点にwindow数取り出す
        correct_label = input_data[i+window_size:i+window_size+1]#index番号がi+windowの値を取り出す。つまりwindowの後にある正解ラベルを取り出す。
        data.append(window_fr)
        target.append(correct_label)

    re_data = np.array(data).reshape(len(data), window_size, 1)#kerasのRNNでは入力をサンプル数,時系列数(window数),入力層のニューロン数にする。　本来なら−１でなくlen(data)?
    re_target = np.array(target).reshape(len(target), 1)#入力と同じにする必要がある。

    return re_data, re_target

window = 7# 学習時のウィンドウサイズ
study_data, correct_data  = sequence_creator(train_normalized, window)

# set parameters
n_in_out = 1
n_hidden = int(args[1])# 2の乗数
drop_out = float(args[2])

print("mlp_n:"+str(n_hidden)+"_dropout:"+str(drop_out))
print("")

# def rmse(y_true, y_pred):
#         return K.sqrt(K.mean(K.square(y_pred - y_true), axis=-1))

# set seed
tf.random.set_seed(0)
#np.random.seed(0)

# define model
model = Sequential()
model.add(Dense(n_hidden,
                batch_input_shape=(None, window, n_in_out),
                activation='relu',
                kernel_initializer='he_normal',
                # kernel_regularizer=regularizers.l1(0.01),
                ))
model.add(Dropout(drop_out))
model.add(Flatten())
model.add(Dense(n_in_out))
model.add(Activation("linear"))
optimizer = Adam(lr=0.001,  amsgrad=False)
model.compile(loss="mse", optimizer=optimizer, metrics=["mae"])#,rmse])
print(model.summary())
print("")

# with open('modelsummary.txt', 'w') as f:
#     with redirect_stdout(f):
#         model.summary()

# filename = 'mlp.png'
# plot_model(model, show_shapes=True, show_layer_names=True, to_file=filename)
# Image(retina=False, filename=filename)

#early_stopping = EarlyStopping(monitor='val_loss', mode='auto', patience=1)
# 学習率を返す関数を用意する
# def lr_schedul(epoch):
#     x = 0.001
#     if epoch >= 50:
#         x = 0.0005
#     return x


# lr_decay = LearningRateScheduler(
#     lr_schedul,
#     # verbose=1で、更新メッセージ表示。0の場合は表示しない
#     verbose=0,
# )

epochs = 1#200
start_time = time.time()
history = model.fit(study_data,
                    correct_data,
                    batch_size=1,
                    shuffle=True,
                    epochs=epochs,
                    validation_split=0.1,
                    verbose=0,
                    callbacks=[]# lr_decay,
                    )

print("学習時間:",time.time() - start_time)
print("")

path = "mlp/model/mlp_"+str(n_hidden)+"_"+str(drop_out)+".h5"
model.save(path)

# === 学習推移の可視化 ===
train_loss = history.history['loss']
val_loss = history.history['val_loss']

path = "mlp/loss/loss_"+str(n_hidden)+"_"+str(drop_out)+".png"
plt.plot(np.arange(len(train_loss)), train_loss, label="train_loss")
plt.plot(np.arange(len(val_loss)), val_loss, label="val_loss")
plt.title('Training and Validation loss', y=-0.25)
plt.xlabel("Epoch(time)")
plt.ylabel("Loss")
# plt.ylim((0, 0.06))#add
plt.legend()
plt.grid(True)
plt.savefig(path)
plt.close()

train_mae = history.history['mae']
val_mae = history.history['val_mae']

path = "mlp/eval_loss/eval_loss_"+str(n_hidden)+"_"+str(drop_out)+".png"
plt.plot(np.arange(len(train_mae)), train_mae, label="train_mae")
plt.plot(np.arange(len(val_mae)), val_mae, label="val_mae")
plt.title('Training and Validation mae', y=-0.25)
plt.xlabel("Epoch(time)")
plt.ylabel("Loss")
#plt.ylim((0, 0.2))#add
plt.legend()
plt.grid(True)
plt.savefig(path)
plt.close()

# train_rmse = history.history['rmse']
# val_rmse = history.history['val_rmse']

# plt.plot(np.arange(len(train_loss)), train_rmse, label="train_rmse")
# plt.plot(np.arange(len(val_loss)), val_rmse, label="val_rmse")
# plt.title('Training and Validation rmse', y=-0.25)
# plt.xlabel("Epoch(time)")
# plt.ylabel("Loss")
# plt.ylim((0, 0.2))#add
# plt.legend()
# plt.grid(True)
# # plt.show()
# plt.savefig(path)
# plt.close()


# training predictions
predicted_past_data = model.predict(study_data)
train_inverse= scaler.inverse_transform(predicted_past_data)

# test predictions
upcoming_future=7
predictions = train_normalized[-window:].tolist()
predictions = np.array(predictions).reshape(-1, window, 1)

for i in range(upcoming_future):
  predicted_future = model.predict(predictions)
  # with open("in_out.txt",mode="a", encoding= "utf-8") as f:
  #   f.write("input to model:" + str(predictions) )
  #   f.write("output from model:" + str(predicted_future) )
  predictions = predictions.tolist()
  predictions = np.append(predictions, predicted_future)
  predictions = predictions[-window:]
  predictions = np.array(predictions).reshape(-1, window, 1)

predictions_infected_pepole = scaler.inverse_transform(np.array(predictions).reshape(-1,1))
# print(predictions_infected_pepole)

x_all =np.arange('2020-01-22','2020-10-29', dtype='datetime64[D]').astype('datetime64[D]')
x_past_predict = np.arange('2020-01-29','2020-10-22', dtype='datetime64[D]').astype('datetime64[D]')
x_train = np.arange('2020-01-22','2020-10-22', dtype='datetime64[D]').astype('datetime64[D]')
x_test = np.arange('2020-10-22', '2020-10-29', dtype='datetime64[D]').astype('datetime64[D]')

# sns.set()
path = "mlp/prediction/prediction_"+str(n_hidden)+"_"+str(drop_out)+".png"
plt.figure(figsize=(20,8))
plt.title('Cumulative confirmed cases in Japan', y=-0.15)
plt.xlabel("Date")
plt.ylabel("Confirmed cases (people)")
# plt.plot(x_train,train_original_data,label='train_data')
# plt.plot(x_test,test_original_data,label='test_data')
plt.plot(x_all, data_at_japan, 'g', lw=3, label='daily_at_japan')
plt.plot(x_past_predict, train_inverse, color='b', ls='-', lw=3, alpha=0.7, label='past_predict')
plt.plot(x_test, predictions_infected_pepole, 'r', lw=3, alpha=0.7, label='upcoming_future')
plt.grid(True)
plt.legend(loc='upper left')
# plt.show()
plt.savefig(path)
plt.close()

# sns.set()
path = "mlp/prediction_detail/prediction_detail_"+str(n_hidden)+"_"+str(drop_out)+".png"
plt.figure(figsize=(20,8))
plt.title('Cumulative confirmed cases in Japan', y=-0.15)
plt.xlabel("Date")
plt.ylabel("Confirmed cases (people)")
plt.plot(x_test, test_original_data,color='b', ls='-',lw=3,alpha=0.7, label='past_predict')
plt.plot(x_test, predictions_infected_pepole, 'r', lw=3, alpha=0.7, label='upcoming_future')
plt.grid(True)
plt.legend(loc='lower left')
# plt.show()
plt.savefig(path)
plt.close()

train_data = train_original_data[7:]
train_mae = mean_absolute_error(train_data, train_inverse)
train_mse = mean_squared_error(train_data, train_inverse)
train_rmse = np.sqrt(mean_squared_error(train_data, train_inverse))
train_r2 = r2_score(train_data, train_inverse)

test_mae = mean_absolute_error(test_original_data, predictions_infected_pepole)
test_mse = mean_squared_error(test_original_data, predictions_infected_pepole)
test_rmse = np.sqrt(mean_squared_error(test_original_data, predictions_infected_pepole))
test_r2 = r2_score(test_original_data, predictions_infected_pepole)

print('train_mae:'+str(train_mae))
print('train_mse:'+str(train_mse))
print('train_rmae:'+str(train_rmse))
print('train_r2:'+str(train_r2))
print('')
print('test_mae:'+str(test_mae))
print('test_mse:'+str(test_mse))
print('test_rmse:'+str(test_rmse))
print('test_r2:'+str(test_r2))# 最も当てはまりの良い場合、1.0 となる (当てはまりの悪い場合、マイナスとなることもある)

# #long term predictions
# x_long_term = np.arange('2020-10-22', '2020-11-21', dtype='datetime64[D]').astype('datetime64[D]')#11-21
# long_term_future = len(x_long_term)
# print(str(long_term_future) + '日間後')

# predictions2 = train_normalized[-window:].tolist()
# predictions2 = np.array(predictions2).reshape(-1, window, 1)

# long_term_predictions = []
# #予測をfor文で
# for i in range(long_term_future):
#   predicted_long_term_future = model.predict(predictions2)
#   long_term_predictions.append(predicted_long_term_future)
#   # with open("in_out_long_term.txt",mode="a", encoding= "utf-8") as f:
#   #   f.write("input to model:" + str(predictions) )
#   #   f.write("output from model:" + str(predicted_future) )
#   predictions2 = predictions2.tolist()
#   predictions2 = np.append(predictions2, predicted_long_term_future)
#   predictions2 = predictions2[-window:]
#   predictions2 = np.array(predictions2).reshape(-1, window, 1)

# predictions_infected_pepole_long_term = scaler.inverse_transform(np.array(long_term_predictions).reshape(-1,1))
# #print(predictions_infected_pepole_long_term)


# sns.set()
# COVID = plt.figure(figsize=(20,8))
# plt.title("COVID-19 in Japan after" + str(long_term_future) + 'days')
# plt.grid(True)
# plt.xlabel("Day(/Day)")
# plt.ylabel("Nunber of Person infected with corona virus(/people)")
# plt.plot(x_all,data_at_japan_diff,'g',lw=3,label='daily_at_japan')
# plt.plot(x_long_term, predictions_infected_pepole_long_term, 'r',lw=3,alpha=0.7,label='upcoming_future')
# plt.legend(loc='upper left')
# plt.show()

