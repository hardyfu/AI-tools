import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from matplotlib.patches import FancyBboxPatch
import os

# Try to find a Chinese font
chinese_fonts = [f for f in fm.findSystemFonts() if any(k in f.lower() for k in ['heiti', 'pingfang', 'stheit', 'songti', 'hiragino', 'noto sans cjk', 'wenyi', 'microsoft yahei', 'simhei', 'simsun'])]
chinese_fonts.sort()
print("Found Chinese fonts:", chinese_fonts)

# Use fallback
plt.rcParams['font.family'] = 'sans-serif'
if chinese_fonts:
    fp = fm.FontProperties(fname=chinese_fonts[0])
    plt.rcParams['font.sans-serif'] = [fm.FontProperties(fname=chinese_fonts[0]).get_name()]
plt.rcParams['axes.unicode_minus'] = False

fig = plt.figure(figsize=(20, 18))
fig.suptitle('西游记 · 数据图解', fontsize=24, fontweight='bold', y=0.98)

# ============================================================
# Chart 1: 唐僧取经数量 (左上)
# ============================================================
ax1 = fig.add_subplot(2, 3, 1)
categories = ['经 (Sutras)', '律 (Vinaya)', '论 (Shastras)', '总计']
values = [1514, 500, 3034, 5048]  # Traditional division approximation
colors1 = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12']

bars = ax1.bar(categories, values, color=colors1, edgecolor='white', linewidth=1.5, width=0.6)
for bar, v in zip(bars, values):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 60, f'{v}卷',
             ha='center', fontsize=12, fontweight='bold')

ax1.set_title('唐僧取经数量 (共5048卷)', fontsize=16, fontweight='bold', pad=15)
ax1.set_ylabel('卷数', fontsize=12)
ax1.set_ylim(0, 5700)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)

# Add annotation
ax1.annotate('一藏之数\n(5048卷)', xy=(3, 5048), xytext=(3.4, 4500),
            fontsize=11, ha='center',
            arrowprops=dict(arrowstyle='->', color='gray', lw=1.5),
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.8))

# ============================================================
# Chart 2: 唐僧取经经书占比 (中上)
# ============================================================
ax2 = fig.add_subplot(2, 3, 2)
categories_pie = ['经 Sutras\n1514卷', '律 Vinaya\n500卷', '论 Shastras\n3034卷']
values_pie = [1514, 500, 3034]
colors_pie = ['#E74C3C', '#3498DB', '#2ECC71']
explode = (0.02, 0.02, 0.02)

wedges, texts, autotexts = ax2.pie(values_pie, explode=explode, labels=categories_pie,
                                     colors=colors_pie, autopct='%1.1f%%',
                                     startangle=90, textprops={'fontsize': 11})
for at in autotexts:
    at.set_fontweight('bold')
    at.set_fontsize(12)
ax2.set_title('经书分布占比', fontsize=16, fontweight='bold', pad=15)

# ============================================================
# Chart 3: 途经国家/地区一览 (右上)
# ============================================================
ax3 = fig.add_subplot(2, 3, 3)
countries = [
    '宝象国', '乌鸡国', '车迟国', '西梁女国', '祭赛国',
    '朱紫国', '狮驼国', '比丘国', '灭法国', '天竺国',
    '凤仙郡', '玉华州', '金平府', '铜台府'
]
# Order by appearance roughly
y_pos = range(len(countries))
encounter_order = list(range(1, len(countries) + 1))

ax3.barh(y_pos, encounter_order, color=plt.cm.viridis(np.linspace(0.2, 0.9, len(countries))),
         edgecolor='white', linewidth=1)
ax3.set_yticks(y_pos)
ax3.set_yticklabels(countries, fontsize=10)
ax3.set_xlabel('途经顺序', fontsize=12)
ax3.set_title('途经国家/地区一览 (共14个主要地区)', fontsize=16, fontweight='bold', pad=15)
ax3.invert_yaxis()
ax3.spines['top'].set_visible(False)
ax3.spines['right'].set_visible(False)

# Add number labels
for i, v in enumerate(encounter_order):
    ax3.text(v + 0.1, i, str(v), va='center', fontsize=9, fontweight='bold')

# ============================================================
# Chart 4: 妖怪实力排行 (左下 - 大图)
# ============================================================
ax4 = fig.add_subplot(2, 3, (4, 5))
demons = [
    '金翅大鹏雕\n(狮驼岭三大王)',
    '九灵元圣\n(九头狮子)',
    '黄眉大王\n(小雷音寺)',
    '青牛精\n(独角兕大王)',
    '牛魔王\n(平天大圣)',
    '六耳猕猴\n(假悟空)',
    '红孩儿\n(圣婴大王)',
    '蝎子精\n(琵琶洞)',
    '白骨精\n(白骨夫人)',
    '黄袍怪\n(奎木狼)'
]
power = [98, 95, 88, 85, 82, 80, 72, 68, 40, 65]
backgrounds = [
    '如来的舅舅\n狮驼国国王', '太乙天尊坐骑\n一吼擒悟空', '弥勒佛童子\n人种袋无敌',
    '太上老君青牛\n金刚琢收万物', '七大圣之首\n力敌悟空八戒', '悟空二心\n诸佛难辨',
    '牛魔王之子\n三昧真火', '倒马毒桩\n如来也怕', '三戏唐僧\n经典反派', '二十八宿之一\n黄袍怪'
]
colors4 = ['#8E44AD', '#E74C3C', '#E67E22', '#2C3E50', '#16A085',
           '#2980B9', '#C0392B', '#8E44AD', '#7F8C8D', '#D35400']

bars4 = ax4.barh(demons, power, color=colors4, edgecolor='white', linewidth=1.2, height=0.7)
for i, (bar, v, bg) in enumerate(zip(bars4, power, backgrounds)):
    ax4.text(v + 0.5, bar.get_y() + bar.get_height()/2, f'{v}分 | {bg}',
             va='center', fontsize=8, color='#333')

ax4.set_title('妖怪实力排行榜 (满分100)', fontsize=16, fontweight='bold', pad=15)
ax4.set_xlabel('实力评分', fontsize=12)
ax4.set_xlim(0, 150)
ax4.invert_yaxis()
ax4.spines['top'].set_visible(False)
ax4.spines['right'].set_visible(False)

# Highlight top 1
bars4[0].set_edgecolor('gold')
bars4[0].set_linewidth(3)
ax4.annotate('最强妖怪', xy=(98, 0), xytext=(105, 0.5),
            fontsize=11, fontweight='bold', color='#8E44AD',
            arrowprops=dict(arrowstyle='->', color='#8E44AD', lw=2))

# ============================================================
# Chart 5: 妖怪实力雷达图 (右下)
# ============================================================
ax5 = fig.add_subplot(2, 3, 6, projection='polar')
categories_radar = ['战斗力', '法宝', '背景靠山', '智谋', '防御力']
top3_demons = ['金翅大鹏雕', '九灵元圣', '黄眉大王']
values_radar = [
    [98, 75, 100, 70, 95],   # 大鹏
    [95, 60, 90, 65, 90],    # 九灵元圣
    [85, 98, 95, 80, 75],    # 黄眉
]
colors_radar = ['#8E44AD', '#E74C3C', '#E67E22']

angles = np.linspace(0, 2 * np.pi, len(categories_radar), endpoint=False).tolist()
angles += angles[:1]

for i, (vals, name, c) in enumerate(zip(values_radar, top3_demons, colors_radar)):
    vals_plot = vals + vals[:1]
    ax5.fill(angles, vals_plot, alpha=0.1, color=c)
    ax5.plot(angles, vals_plot, 'o-', linewidth=2, label=name, color=c, markersize=6)

ax5.set_xticks(angles[:-1])
ax5.set_xticklabels(categories_radar, fontsize=11)
ax5.set_ylim(0, 100)
ax5.set_title('TOP3 妖怪能力雷达图', fontsize=16, fontweight='bold', pad=20)
ax5.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=10)
ax5.set_yticks([20, 40, 60, 80, 100])
ax5.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=8)

plt.tight_layout(rect=[0, 0, 1, 0.95])
output_path = '/Users/ryanfu/Desktop/pythoncode/journey_to_west_charts.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print(f"Chart saved to {output_path}")
