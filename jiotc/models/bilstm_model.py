# -*- coding=utf-8 -*-

# author: dongrixinyu
# contact: dongrixinyu.89@163.com
# blog: https://eliyar.biz

# file: bare_embedding.py
# time: 2020-06-12 11:27

import os
import pdb
import logging
from typing import Union, Optional, Dict, Any, Tuple


import torch
import torch.nn as nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence

from text_classification.embeddings.base_embedding import BaseEmbedding
from .base_model import BaseModel

# Bidirectional LSTM neural network (many-to-one)
class BiLSTM_Model(nn.Module):
    
    @classmethod
    def get_default_hyper_parameters(cls) -> Dict[str, Dict[str, Any]]:
        return {
            'layer_bi_lstm': {
                'hidden_size': 128,
                'num_layers': 1,
                'dropout': 0.2,  # 当 num_layers == 1 时失效
                'bidirectional': True
            },
            'layer_dense': {
                'activation': 'softmax'
            }
        }
    
    def __init__(self, embed_model: Optional[BaseEmbedding] = None, 
                 device: Union['cuda', 'cpu'] = None,
                 hyper_parameters: Optional[Dict[str, Dict[str, Any]]] = None):
        
        super(BiLSTM_Model, self).__init__()
        
        self.embedding = embed_model
        
        if device is None:
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            device = torch.device(device)
        self.device = device
        
        self.hidden_size = hyper_parameters['layer_bi_lstm']['hidden_size']
        self.num_layers = hyper_parameters['layer_bi_lstm']['num_layers']
        
        # 构建 embedding 以及预处理时已经确定的参数，可以复制
        self.embedding_size = self.embedding.embedding_size
        self.num_classes = len(self.embedding.label2idx)
        
        #pdb.set_trace()
        self.lstm = nn.LSTM(
            self.embedding_size, self.hidden_size, self.num_layers, 
            batch_first=True, bidirectional=True)#.to(self.device)
        
        self.fc = nn.Linear(self.hidden_size * 2,
                            self.num_classes)#.to(self.device)  # 2 for bidirection

    def forward(self, samples):
        
        masks = samples.gt(0)
        embeds = self.embedding.embedding_layer(samples).to(self.device)
        
        # 按长短调整样本顺序
        seq_length = masks.sum(1)
        sorted_seq_length, perm_idx = seq_length.sort(descending=True)
        embeds = embeds[perm_idx, :]
        
        pack_sequence = pack_padded_sequence(
            embeds, lengths=sorted_seq_length, batch_first=True)
        
        # Set initial states, involved with batch_size
        h0 = torch.autograd.Variable(torch.randn(
            self.num_layers * 2, embeds.shape[0],
            self.hidden_size)).to(self.device)  # 2 for bidirection 
        c0 = torch.autograd.Variable(torch.randn(
            self.num_layers * 2, embeds.shape[0], 
            self.hidden_size)).to(self.device)
        
        # Forward propagate LSTM
        packed_output, _ = self.lstm(pack_sequence, (h0, c0))
        # out: tensor of shape (batch_size, seq_length, hidden_size*2)
        
        lstm_out, _ = pad_packed_sequence(packed_output, batch_first=True)
        _, unperm_idx = perm_idx.sort()
        lstm_out = lstm_out[unperm_idx, :]
        
        # Decode the hidden state of the last time step
        out = self.fc(lstm_out[:, -1, :])
        return out


if __name__ == '__main__':
    model = BiLSTM(4, 4, 2, 2).to('cpu')
    print(model)
    print(type(model))
    pdb.set_trace()



