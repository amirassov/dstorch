import random

import numpy as np
from torch import nn
from tqdm import tqdm

from dstorch.utils import variable


def validation_binary(model: nn.Module, criterion, val_loader):
    model.eval()
    losses = []
    
    for inputs, targets in val_loader:
        inputs = variable(inputs, volatile=True)
        targets = variable(targets)
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        losses.append(loss.data[0])
    
    valid_loss = np.mean(losses)

    print('Valid loss: {:.5f}'.format(valid_loss))
    metrics = {'valid_loss': valid_loss}
    return metrics


def cyclic_lr(epoch, init_lr=5e-4, num_epochs_per_cycle=5, cycle_epochs_decay=2, lr_decay_factor=0.5):
    epoch_in_cycle = epoch % num_epochs_per_cycle
    lr = init_lr * (lr_decay_factor ** (epoch_in_cycle // cycle_epochs_decay))
    return lr


def train(model, n_epochs, batch_size, criterion, train_loader, val_loader, init_optimizer, lr):
    epoch, report_each, valid_losses = 1, 10, []
    for epoch in range(epoch, n_epochs + 1):
        lr = cyclic_lr(epoch)
        optimizer = init_optimizer(lr)
        
        model.train()
        random.seed()
        
        bar = tqdm(total=(len(train_loader) * batch_size))
        bar.set_description('Epoch {}, lr {}'.format(epoch, lr))
        losses = []
        _train_loader = train_loader
        
        try:
            for i, (inputs, targets) in enumerate(_train_loader):
                inputs, targets = variable(inputs), variable(targets)
                outputs = model(inputs)
                
                loss = criterion(outputs, targets)
                
                optimizer.zero_grad()
                batch_size = inputs.size(0)
                loss.backward()
                optimizer.step()
                
                bar.update(batch_size)
                losses.append(loss.data[0])
                mean_loss = np.mean(losses[-report_each:])
                bar.set_postfix(loss='{:.5f}'.format(mean_loss))

            bar.close()
            valid_metrics = validation_binary(model, criterion, val_loader)
            valid_loss = valid_metrics['valid_loss']
            valid_losses.append(valid_loss)
        
        except KeyboardInterrupt:
            bar.close()
            print('done.')
            return valid_losses
    return valid_losses
