#!/usr/bin/env python

# Eugenio Culurciello, May 2017
# fine tune on OIRDS dataset
# updated code from: http://pytorch.org/tutorials/beginner/transfer_learning_tutorial.html

from __future__ import print_function, division

import torch
import torch.nn as nn
import torch.optim as optim
from torch.autograd import Variable
import numpy as np
import torchvision
from torchvision import datasets, models, transforms
# import matplotlib.pyplot as plt
import time
import copy
import os, sys
from tqdm import tqdm, trange


print('Usage: python3 finetune.py resnet18/alexnet')
   

def imshow(inp, title=None):
    """Imshow for Tensor."""
    inp = inp.numpy().transpose((1, 2, 0))
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    inp = std * inp + mean
    plt.imshow(inp)
    plt.axis('off')
    if title is not None:
        plt.title(title)
    plt.pause(0.001)  # pause a bit so that plots are updated



def train_model(model, criterion, optimizer, num_epochs=25):
    since = time.time()

    best_model = model
    best_acc = 0.0

    for epoch in range(num_epochs):
        print('Epoch {}/{}'.format(epoch, num_epochs - 1))
        print('-' * 10)

        # Each epoch has a training and validation phase
        for phase in ['train', 'val']:
            if phase == 'train':
                optimizer = optimizer
                model.train()  # Set model to training mode
            else:
                model.eval()  # Set model to evaluate mode

            running_loss = 0.0
            running_corrects = 0

            # Iterate over data.
            pbar = tqdm( total=len(dset_loaders[phase]) )
            for data in dset_loaders[phase]:
                pbar.update(1)
                # get the inputs
                inputs, labels = data

                # wrap them in Variable
                if use_gpu:
                    inputs, labels = Variable(inputs.cuda()), \
                        Variable(labels.cuda())
                else:
                    inputs, labels = Variable(inputs), Variable(labels)

                # zero the parameter gradients
                optimizer.zero_grad()

                # forward
                outputs = model(inputs)
                _, preds = torch.max(outputs.data, 1)
                loss = criterion(outputs, labels)

                # backward + optimize only if in training phase
                if phase == 'train':
                    loss.backward()
                    optimizer.step()

                # statistics
                running_loss += loss.data[0]
                running_corrects += torch.sum(preds == labels.data)

            epoch_loss = running_loss / dset_sizes[phase]
            epoch_acc = running_corrects / dset_sizes[phase]

            print('{} Loss: {:.4f} Acc: {:.4f}'.format(
                phase, epoch_loss, epoch_acc))

            # deep copy the model
            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model = copy.deepcopy(model)

        print()

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(
        time_elapsed // 60, time_elapsed % 60))
    print('Best val Acc: {:4f}'.format(best_acc))
    return best_model


# MAIN:

# plt.ion()   # interactive mode

# params:
batch_size = 128
threads = 8

# Data augmentation and normalization for training
# Just normalization for validation
data_transforms = {
    'train': transforms.Compose([
     transforms.RandomSizedCrop(224),
     transforms.RandomHorizontalFlip(),
     transforms.ToTensor(),
     transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ]),
    'val': transforms.Compose([
     transforms.Scale(256),
     transforms.CenterCrop(224),
     transforms.ToTensor(),
     transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ]),
}

data_dir = 'data/oirds/'
dsets = {x: datasets.ImageFolder(os.path.join(data_dir, x), data_transforms[x])
         for x in ['train', 'val']}
dset_loaders = {x: torch.utils.data.DataLoader(dsets[x], batch_size=batch_size,
                                               shuffle=True, num_workers=threads)
                for x in ['train', 'val']}
dset_sizes = {x: len(dsets[x]) for x in ['train', 'val']}
dset_classes = dsets['train'].classes

use_gpu = torch.cuda.is_available()


# Get a batch of training data
inputs, classes = next(iter(dset_loaders['train']))

# Make a grid from batch
# out = torchvision.utils.make_grid(inputs)
# imshow(out, title=[dset_classes[x] for x in classes])

if sys.argv[1] == 'resnet18':
    print('Load pre-trained model, resnet18')
    model_ft = models.resnet18(pretrained=True)
    num_ftrs = model_ft.fc.in_features
    model_ft.fc = nn.Linear(num_ftrs, 2)
    print(model_ft)
    optimizer_ft = optim.Adam( model_ft.parameters() ) # used for ResNet18
    file_modeldef = "modelDef-resnet18.pth"
    file_model = "finemodel-resnet18.pth"
elif sys.argv[1] == 'alexnet':
    print('Load pre-trained model, alexnet')
    model_ft = models.alexnet(pretrained=True)
    # print(list(list(model_ft.classifier.children())[1].parameters()))
    mod = list(model_ft.classifier.children())
    mod.pop()
    mod.append(torch.nn.Linear(4096, 2))
    new_classifier = torch.nn.Sequential(*mod)
    # print(list(list(new_classifier.children())[1].parameters()))
    model_ft.classifier = new_classifier
    print(model_ft)
    optimizer_ft = optim.SGD(model_ft.parameters(), lr = 0.01, momentum=0.9)
    file_modeldef = "modelDef-alexnet.pth"
    file_model = "finemodel-alexnet.pth"
else:
    print('Model not supported!')
    sys.exit(0)

# continue:
print('use GPU is needed')
if use_gpu:
    model_ft = model_ft.cuda()

criterion = nn.CrossEntropyLoss()

print('Training model:')
model_ft = train_model(model_ft, criterion, optimizer_ft, num_epochs=25)

# save best model:
torch.save(model_ft, file_modeldef)
torch.save(model_ft.state_dict(), file_model)
