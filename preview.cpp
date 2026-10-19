#include <QApplication>
#include <QCheckBox>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QPixmap>
#include <QPushButton>
#include <QVBoxLayout>
#include <QWidget>
int main(int argc, char **argv) {
    QApplication app(argc, argv);
    if (argc != 3) return 2;
    QWidget window;
    window.setWindowTitle("iNiR Qt palette check");
    auto *layout = new QVBoxLayout(&window);
    layout->setContentsMargins(24,24,24,24);
    layout->setSpacing(14);
    auto *title = new QLabel(QString::fromUtf8(argv[1]));
    auto font = title->font(); font.setPointSize(16); font.setBold(true); title->setFont(font);
    layout->addWidget(title);
    layout->addWidget(new QLabel("Qt 6 Widgets · Breeze · qt6ct"));
    auto *field = new QLineEdit;
    field->setPlaceholderText("Search applications");
    layout->addWidget(field);
    auto *list = new QListWidget;
    list->addItems({"Files", "Downloads", "Pictures"});
    list->setCurrentRow(0);
    layout->addWidget(list);
    auto *check = new QCheckBox("Use the selected palette"); check->setChecked(true); layout->addWidget(check);
    auto *buttons = new QHBoxLayout;
    auto *disabled = new QPushButton("Unavailable"); disabled->setEnabled(false);
    buttons->addWidget(disabled); buttons->addStretch(); buttons->addWidget(new QPushButton("Cancel"));
    auto *apply = new QPushButton("Apply"); apply->setDefault(true); buttons->addWidget(apply);
    layout->addLayout(buttons);
    window.resize(460,380); window.show(); app.processEvents();
    return window.grab().save(QString::fromLocal8Bit(argv[2])) ? 0 : 1;
}
