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


def adjust_lr(epoch, init_lr=0.0005, num_epochs_per_decay=50, lr_decay_factor=0.2):
    lr = init_lr * (lr_decay_factor ** (epoch // num_epochs_per_decay))
    return lr


def cyclic_lr(epoch, init_lr=3e-4, num_epochs_per_cycle=30, cycle_epochs_decay=10, lr_decay_factor=0.5):
    epoch_in_cycle = epoch % num_epochs_per_cycle
    lr = init_lr * (lr_decay_factor ** (epoch_in_cycle // cycle_epochs_decay))
    return lr


def train(
        model, n_epochs, batch_size,
        criterion, train_loader,
        val_loader, init_optimizer,
        cyclic_lr_params=None
):
    report_each, val_losses = 10, []
    for epoch in range(1, n_epochs + 1):
        lr = cyclic_lr(epoch, **cyclic_lr_params)
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
            val_losses.append(valid_loss)
        
        except KeyboardInterrupt:
            bar.close()
            print('done.')
            return val_losses
    return val_losses
