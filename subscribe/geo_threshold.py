#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
地理位置智能阈值模块
根据节点地理位置动态调整延迟阈值
"""

import re
from typing import Tuple, Dict, List

# 地理位置分级配置
# 考虑从中国大陆访问各地的实际网络情况
GEO_REGIONS = {
    # 一级：港澳台 - 距离最近，网络最好
    'tier1_hk_tw': {
        'name': '港澳台地区',
        'keywords': [
            '香港', 'HK', 'Hong Kong', 'HongKong', 'HGC', '🇭🇰',
            '澳门', 'Macau', 'Macao', '🇲🇴',
            '台湾', 'TW', 'Taiwan', 'Taipei', '台北', '🇹🇼',
        ],
        'base_threshold': 800,      # 基础阈值(ms) - 巴西测试时期望的延迟上限
        'multiplier': 1.0,          # 阈值倍数
        'priority': 1,              # 优先级（数字越小优先级越高）
        'description': '距离中国最近，通常<50ms延迟',
    },
    
    # 二级：亚洲邻近国家 - 网络质量优秀
    'tier2_asia_near': {
        'name': '亚洲邻近',
        'keywords': [
            '日本', 'JP', 'Japan', 'Tokyo', '东京', 'Osaka', '大阪', '🇯🇵',
            '韩国', 'KR', 'Korea', 'Seoul', '首尔', '🇰🇷',
            '新加坡', 'SG', 'Singapore', '狮城', '🇸🇬',
        ],
        'base_threshold': 1200,
        'multiplier': 1.2,
        'priority': 2,
        'description': '亚洲邻近，通常50-100ms延迟',
    },
    
    # 三级：东南亚 - 网络质量良好
    'tier3_southeast_asia': {
        'name': '东南亚',
        'keywords': [
            '越南', 'VN', 'Vietnam', 'Hanoi', 'Saigon', '🇻🇳',
            '泰国', 'TH', 'Thailand', 'Bangkok', '曼谷', '🇹🇭',
            '马来西亚', 'MY', 'Malaysia', 'Kuala', '吉隆坡', '🇲🇾',
            '菲律宾', 'PH', 'Philippines', 'Manila', '🇵🇭',
            '印尼', 'ID', 'Indonesia', 'Jakarta', '🇮🇩',
            '印度', 'IN', 'India', 'Mumbai', 'Delhi', '🇮🇳',
        ],
        'base_threshold': 1500,
        'multiplier': 1.5,
        'priority': 3,
        'description': '东南亚地区，通常100-150ms延迟',
    },
    
    # 四级：美国西海岸 - 太平洋线路优质
    'tier4_us_west': {
        'name': '美西',
        'keywords': [
            '洛杉矶', 'Los Angeles', 'LA', 'LAX',
            '圣何塞', 'San Jose', 'SJ',
            '旧金山', 'San Francisco', 'SF', 'SFO',
            '西雅图', 'Seattle', 'SEA',
            '波特兰', 'Portland',
            '圣地亚哥', 'San Diego',
            '硅谷', 'Silicon Valley',
            '俄勒冈', 'Oregon',
        ],
        'base_threshold': 1800,
        'multiplier': 1.8,
        'priority': 4,
        'description': '美国西海岸，通常150-200ms延迟',
    },
    
    # 五级：美国中部及东海岸、加拿大
    'tier5_us_east_ca': {
        'name': '美东/加拿大',
        'keywords': [
            '美国', 'US', 'USA', 'United States', 'America', '🇺🇸',
            '纽约', 'New York', 'NY', 'NYC',
            '华盛顿', 'Washington', 'DC',
            '芝加哥', 'Chicago',
            '达拉斯', 'Dallas',
            '迈阿密', 'Miami',
            '亚特兰大', 'Atlanta',
            '凤凰城', 'Phoenix',
            '丹佛', 'Denver',
            '加拿大', 'Canada', 'Toronto', '多伦多', 'Vancouver', '温哥华', '🇨🇦',
        ],
        'base_threshold': 2200,
        'multiplier': 2.2,
        'priority': 5,
        'description': '美国东部/加拿大，通常200-250ms延迟',
    },
    
    # 六级：欧洲
    'tier6_europe': {
        'name': '欧洲',
        'keywords': [
            '英国', 'UK', 'Britain', 'London', '伦敦', '🇬🇧',
            '德国', 'DE', 'Germany', 'Frankfurt', '法兰克福', 'Berlin', '🇩🇪',
            '法国', 'FR', 'France', 'Paris', '巴黎', '🇫🇷',
            '荷兰', 'NL', 'Netherlands', 'Amsterdam', '阿姆斯特丹', '🇳🇱',
            '俄罗斯', 'RU', 'Russia', 'Moscow', '莫斯科', '🇷🇺',
            '意大利', 'IT', 'Italy', 'Rome', 'Milan', '🇮🇹',
            '西班牙', 'ES', 'Spain', 'Madrid', '🇪🇸',
            '瑞士', 'CH', 'Switzerland', '🇨🇭',
            '瑞典', 'SE', 'Sweden', '🇸🇪',
            '波兰', 'PL', 'Poland', '🇵🇱',
            '乌克兰', 'Ukraine', '🇺🇦',
        ],
        'base_threshold': 2800,
        'multiplier': 2.8,
        'priority': 6,
        'description': '欧洲地区，通常250-350ms延迟',
    },
    
    # 七级：南美、非洲、大洋洲
    'tier7_others': {
        'name': '其他地区',
        'keywords': [
            '巴西', 'BR', 'Brazil', 'Sao Paulo', '🇧🇷',
            '阿根廷', 'Argentina', 'AR', '🇦🇷',
            '智利', 'Chile', 'CL', '🇨🇱',
            '南非', 'South Africa', 'ZA', '🇿🇦',
            '澳大利亚', 'Australia', 'AU', 'Sydney', 'Melbourne', '🇦🇺',
            '新西兰', 'New Zealand', 'NZ', '🇳🇿',
            '土耳其', 'Turkey', 'TR', '🇹🇷',
            '以色列', 'Israel', 'IL', '🇮🇱',
            '阿联酋', 'UAE', 'Dubai', '🇦🇪',
        ],
        'base_threshold': 3500,
        'multiplier': 3.5,
        'priority': 7,
        'description': '南美/非洲/大洋洲，通常350-500ms延迟',
    },
}

# 特殊关键词（IPLC、IEPL等专线）- 应该使用更严格的标准
SPECIAL_KEYWORDS = {
    'premium': {
        'keywords': ['IPLC', 'IEPL', '专线', '专用', 'Premium', 'Pro', 'VIP', '高级'],
        'multiplier': 0.8,  # 降低20%阈值，要求更严格
        'description': '专线/高级线路，期望更低延迟',
    },
    'relay': {
        'keywords': ['中转', 'Relay', '中继', '转发'],
        'multiplier': 1.0,  # 保持标准阈值
        'description': '中转节点，标准要求',
    },
    'direct': {
        'keywords': ['直连', 'Direct', '直通'],
        'multiplier': 0.9,  # 略微降低阈值
        'description': '直连节点，期望较低延迟',
    },
}


class GeoThresholdManager:
    """地理位置阈值管理器"""
    
    def __init__(self, base_threshold: int = 2500):
        """
        初始化管理器
        
        Args:
            base_threshold: 全局基础阈值(ms)，用于未识别地区的节点
        """
        self.base_threshold = base_threshold
        self.stats = {
            'total': 0,
            'matched': 0,
            'unmatched': 0,
            'by_region': {},
        }
    
    def get_threshold(self, node_name: str) -> Tuple[int, str, int]:
        """
        根据节点名称获取动态阈值
        
        Args:
            node_name: 节点名称
            
        Returns:
            (阈值ms, 地区名称, 优先级)
        """
        self.stats['total'] += 1
        
        if not node_name:
            return self.base_threshold, '未知', 999
        
        node_name_clean = node_name.strip()
        
        # 1. 检查特殊关键词（专线等）
        special_multiplier = 1.0
        special_matched = False
        for special_type, config in SPECIAL_KEYWORDS.items():
            for keyword in config['keywords']:
                if keyword.lower() in node_name_clean.lower():
                    special_multiplier = config['multiplier']
                    special_matched = True
                    break
            if special_matched:
                break
        
        # 2. 检查地理位置
        for region_key, region_config in GEO_REGIONS.items():
            for keyword in region_config['keywords']:
                # 使用正则表达式进行更精确的匹配
                # 避免误匹配（如 "CHina" 不应该匹配到 "CH" 瑞士）
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, node_name_clean, re.IGNORECASE):
                    # 计算最终阈值
                    final_threshold = int(
                        region_config['base_threshold'] * 
                        special_multiplier
                    )
                    
                    # 统计
                    self.stats['matched'] += 1
                    region_name = region_config['name']
                    self.stats['by_region'][region_name] = \
                        self.stats['by_region'].get(region_name, 0) + 1
                    
                    return (
                        final_threshold,
                        region_name,
                        region_config['priority']
                    )
        
        # 3. 未匹配到任何地区，使用全局基础阈值
        self.stats['unmatched'] += 1
        return self.base_threshold, '未知地区', 999
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()
    
    def print_stats(self):
        """打印统计信息"""
        print("\n" + "="*60)
        print("地理位置识别统计")
        print("="*60)
        print(f"总节点数: {self.stats['total']}")
        print(f"已识别: {self.stats['matched']} ({self.stats['matched']/max(self.stats['total'],1)*100:.1f}%)")
        print(f"未识别: {self.stats['unmatched']} ({self.stats['unmatched']/max(self.stats['total'],1)*100:.1f}%)")
        
        if self.stats['by_region']:
            print("\n各地区分布:")
            # 按数量排序
            sorted_regions = sorted(
                self.stats['by_region'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for region, count in sorted_regions:
                print(f"  {region:12s}: {count:4d} 个节点")
        print("="*60 + "\n")


def test_geo_threshold():
    """测试函数"""
    manager = GeoThresholdManager(base_threshold=2500)
    
    test_nodes = [
        "🇭🇰 香港-IPLC-01",
        "香港 HKT BGP",
        "🇯🇵 日本东京 NTT",
        "日本大阪-高速",
        "🇸🇬 新加坡-专线",
        "新加坡 AWS",
        "🇺🇸 美国洛杉矶 CN2 GIA",
        "美国西雅图",
        "🇺🇸 美国纽约",
        "🇨🇦 加拿大多伦多",
        "🇬🇧 英国伦敦",
        "🇩🇪 德国法兰克福",
        "🇷🇺 俄罗斯莫斯科",
        "🇦🇺 澳大利亚悉尼",
        "🇧🇷 巴西圣保罗",
        "台湾-中华电信",
        "韩国首尔 KT",
        "泰国曼谷",
        "越南胡志明",
        "土耳其伊斯坦布尔",
        "未知节点-X",
        "测试节点123",
    ]
    
    print("\n节点阈值测试:")
    print("="*80)
    print(f"{'节点名称':<35s} {'阈值(ms)':<12s} {'地区':<12s} {'优先级':<8s}")
    print("="*80)
    
    for node in test_nodes:
        threshold, region, priority = manager.get_threshold(node)
        print(f"{node:<35s} {threshold:<12d} {region:<12s} {priority:<8d}")
    
    manager.print_stats()
    
    # 显示配置说明
    print("\n地理位置分级说明:")
    print("="*80)
    for idx, (key, config) in enumerate(GEO_REGIONS.items(), 1):
        print(f"\n第{idx}级 - {config['name']}:")
        print(f"  基础阈值: {config['base_threshold']}ms")
        print(f"  {config['description']}")
        print(f"  关键词示例: {', '.join(config['keywords'][:5])}...")
    
    print("\n特殊线路调整:")
    print("="*80)
    for key, config in SPECIAL_KEYWORDS.items():
        print(f"\n{key}:")
        print(f"  倍数: {config['multiplier']}")
        print(f"  {config['description']}")
        print(f"  关键词: {', '.join(config['keywords'])}")


if __name__ == '__main__':
    test_geo_threshold()

