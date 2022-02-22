
# This program attempts to fit a DNN to the MNIST dataset with random target labels
# Results show this does not work well

import tensorflow as tf
import numpy as np
import torch
import torchvision as tv
from torchvision import transforms, datasets
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import matplotlib.pyplot as plt
plt.style.use('seaborn-whitegrid')
print(tf.__version__)





randomLabelsTrain = torch.tensor(np.random.randint(0,10, (len(trainingSet)),))
trainingSet.targets = randomLabelsTrain
randomLabelsTest = torch.tensor(np.random.randint(0,10, (len(testingSet)),))
testingSet.targets = randomLabelsTest


train = torch.utils.data.DataLoader(trainingSet, batch_size=75, shuffle=True)
test = torch.utils.data.DataLoader(testingSet, batch_size=75, shuffle=True)

trainingSet = datasets.MNIST('', train=True, download=True, transform=transforms.Compose([transforms.ToTensor()]))
testingSet = datasets.MNIST('', train=False, download=True, transform=transforms.Compose([transforms.ToTensor()]))

class randomNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(784, 20)
        self.fc2 = nn.Linear(20, 15)
        self.fc3 = nn.Linear(15, 10)

    def forward(self, val):
        val = F.relu(self.fc1(val))
        val = F.relu(self.fc2(val))
        val = self.fc3(val)
        return val


randomNet = randomNN()
costFunc = nn.CrossEntropyLoss()
opt = optim.Adam(randomNet.parameters(), lr=0.001)


EPOCHS = 120
counter = 0
counterList = []
costList = []
testLossList = []
trainLossList = []
for index in range(EPOCHS):
    counterList.append(counter)
    counter += 1
   
    for batch in train:
        inputImages, groundTruth = batch
        randomNet.zero_grad()
        output = randomNet(inputImages.view(-1,784))
        cost = costFunc(output, groundTruth)
        cost.backward()
        opt.step()
    costList.append(cost)
    
    
    trainTotal = 0
    trainCounter = 0
    for batch in train: 
        inputImages, groundTruth = batch
        output = randomNet(inputImages.view(-1,784))
        cost = costFunc(output, groundTruth)
        trainTotal += cost
        trainCounter += 1
    trainTotal = trainTotal / trainCounter
    trainLossList.append(trainTotal)
    
    
    testTotal = 0
    testCounter = 0
    for batch in test: 
        inputImages, groundTruth = batch
        output = randomNet(inputImages.view(-1,784))
        cost = costFunc(output, groundTruth)
        testTotal += cost
        testCounter += 1
    testTotal = testTotal / testCounter
    testLossList.append(testTotal)

def calcParams(inputModel):
    val = sum(params.numel() for params in inputModel.parameters() if params.requires_grad)
    return val
print(calcParams(randomNN()))


plt.plot(counterList, trainLossList, 'b.', label='Train')
plt.plot(counterList, testLossList, 'g.', label='Test')
plt.title("Loss on Random Labels")
plt.xlabel("EPHOCS")
plt.ylabel("Loss")
plt.legend(loc="center")
plt.show()
