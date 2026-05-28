import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

class SimpleCNN(nn.Module):
    def __init__(self):
        super(SimpleCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
        )
        # after two 2x2 pools, 28x28 -> 7x7
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 7 * 7, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, 10),
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x
def train(model, device, train_loader, optimizer, crit):
    model.train()
    total_loss = 0
    for id, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = crit(output, target)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    avg_loss = total_loss / len(train_loader)
    return avg_loss
def validate(model, device, val_loader, crit):
    model.eval()
    val_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in val_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            val_loss += crit(output, target).item()
            pred = output.argmax(dim=1, keepdim=True)
            correct += pred.eq(target.view_as(pred)).sum().item()
    val_loss /= len(val_loader)
    accuracy = correct / len(val_loader.dataset)
    return val_loss, accuracy
def main():
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    train_dataset = datasets.MNIST(
        root="./data",
        train=True,
        download=True,
        transform=transform
    )
    val_dataset = datasets.MNIST(
        root="./data",
        train=False,
        download=True,
        transform=transform
    )
    train_loader = DataLoader(
        train_dataset,
        batch_size=64,
        shuffle=True
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=64,
        shuffle=False
    )
    model = SimpleCNN().to(device)
    optimizer = optim.Adam(
        model.parameters(),
        lr=0.001
    )
    crit = nn.CrossEntropyLoss()
    for epoch in range(1, 10):
        train_loss = train(
            model,
            device,
            train_loader,
            optimizer,
            crit
        )
        val_loss, accuracy = validate(
            model,
            device,
            val_loader,
            crit
        )
        print(f"Epoch {epoch}")
        print(f"Training Loss: {train_loss:.4f}")
        print(f"Validation Loss: {val_loss:.4f}")
        print(f"Accuracy: {accuracy * 100:.2f}%")
        print("-" * 30)
if __name__ == "__main__":
    main()
