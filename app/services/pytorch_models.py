# app/services/pytorch_models.py (NUEVO ARCHIVO)

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

class VotingClassifier(nn.Module):
    """Red Neuronal para Clasificación de Votos"""
    
    def __init__(self, input_size: int, num_classes: int):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            
            nn.Linear(64, 32),
            nn.ReLU(),
            
            nn.Linear(32, num_classes)
        )
    
    def forward(self, x):
        return self.network(x)


async def train_pytorch_model(X_train, y_train, X_test, y_test, num_classes):
    """Entrena modelo PyTorch"""
    
    # Convertir a tensors
    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.LongTensor(y_train.values)
    X_test_t = torch.FloatTensor(X_test)
    y_test_t = torch.LongTensor(y_test.values)
    
    # DataLoader
    train_dataset = TensorDataset(X_train_t, y_train_t)
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    
    # Modelo
    model = VotingClassifier(X_train.shape[1], num_classes)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Entrenamiento
    epochs = 50
    for epoch in range(epochs):
        model.train()
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
    
    # Evaluación
    model.eval()
    with torch.no_grad():
        predictions = model(X_test_t).argmax(dim=1)
        accuracy = (predictions == y_test_t).float().mean().item()
    
    return {
        "model": model,
        "accuracy": accuracy,
        "framework": "PyTorch"
    }