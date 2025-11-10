#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
地理位置智能阈值模块 V2 - 修正版
适用于远程服务器测试场景

核心策略调整：
- 对于亚洲节点：使用更宽松的阈值（避免误杀优质节点）
- 对于欧美节点：使用较严格的阈值（避免保留劣质节点）
- 对于CDN/不确定节点：使用全局阈值
"""

import re
from typing import Tuple, Dict, List

# 修正后的地理位置分级配置
# 从远程服务器（如巴西）测试时的策略
GEO_REGIONS = {
    # 一级：港澳台 - 重点保护！使用最宽松阈值
    'tier1_hk_tw': {
        'name': '港澳台地区',
        'keywords': [
            '香港', 'HK', 'Hong Kong', 'HongKong', 'HGC', '🇭🇰',
            '澳门', 'Macau', 'Macao', '🇲🇴',
            '台湾', 'TW', 'Taiwan', 'Taipei', '台北', '🇹🇼',
        ],
        'base_threshold': 3500,     # 使用最高阈值！
        'multiplier': 1.4,          # 额外增加40%
        'priority': 1,
        'description': '距离中国最近，必须保留！从巴西测试延迟可能很高',
    },
    
    # 二级：日韩新 - 核心亚洲节点，高度保护
    'tier2_jp_kr_sg': {
        'name': '日韩新',
        'keywords': [
            '日本', 'JP', 'Japan', 'Tokyo', '东京', 'Osaka', '大阪', '🇯🇵',
            '韩国', 'KR', 'Korea', 'Seoul', '首尔', '🇰🇷',
            '新加坡', 'SG', 'Singapore', '狮城', '🇸🇬',
        ],
        'base_threshold': 3200,
        'multiplier': 1.3,
        'priority': 2,
        'description': '核心亚洲节点，对中国用户最优，必须保护',
    },
    
    # 三级：其他亚洲 - 同样重要
    'tier3_asia_other': {
        'name': '其他亚洲',
        'keywords': [
            '越南', 'VN', 'Vietnam', 'Hanoi', 'Saigon', '🇻🇳',
            '泰国', 'TH', 'Thailand', 'Bangkok', '曼谷', '🇹🇭',
            '马来西亚', 'MY', 'Malaysia', 'Kuala', '吉隆坡', '🇲🇾',
            '菲律宾', 'PH', 'Philippines', 'Manila', '🇵🇭',
            '印尼', 'ID', 'Indonesia', 'Jakarta', '🇮🇩',
            '印度', 'IN', 'India', 'Mumbai', 'Delhi', '🇮🇳',
        ],
        'base_threshold': 3000,
        'multiplier': 1.2,
        'priority': 3,
        'description': '亚洲其他地区，对中国用户仍然很好',
    },
    
    # 四级：美国西海岸 - 可接受
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
        'base_threshold': 2200,
        'multiplier': 1.0,
        'priority': 4,
        'description': '美国西海岸，太平洋线路',
    },
    
    # 五级：美国其他地区和加拿大 - 一般
    'tier5_us_other_ca': {
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
        'base_threshold': 2000,
        'multiplier': 0.95,
        'priority': 5,
        'description': '美国东部和加拿大，距离较远',
    },
    
    # 六级：欧洲 - 较严格
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
        'base_threshold': 1800,
        'multiplier': 0.9,
        'priority': 6,
        'description': '欧洲地区，对中国用户一般',
    },
    
    # 七级：其他远距离地区 - 最严格
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
        'base_threshold': 1500,
        'multiplier': 0.8,
        'priority': 7,
        'description': '南美/非洲/大洋洲，对中国用户较差',
    },
}

# 特殊关键词处理
SPECIAL_KEYWORDS = {
    'premium': {
        'keywords': ['IPLC', 'IEPL', '专线', '专用', 'Premium', 'Pro', 'VIP', '高级', 'CN2', 'GIA'],
        'multiplier': 1.15,  # 专线节点额外增加15%阈值（更宽松）
        'description': '专线/高级线路，优先保留',
    },
    'direct': {
        'keywords': ['Direct', '直连', '直通'],
        'multiplier': 1.1,   # 直连节点额外增加10%
        'description': '直连节点，优先保留',
    },
    'relay': {
        'keywords': ['Relay', '中转', '中继', '转发'],
        'multiplier': 1.05,  # 中转节点额外增加5%
        'description': '中转节点，适当保留',
    },
    # CDN节点特殊处理
    'cdn': {
        'keywords': ['CloudFlare', 'CF', 'CDN', '104.', '172.', 'Cloudflare'],
        'multiplier': 0.8,   # CDN节点使用较严格标准
        'description': 'CDN节点，可能不稳定',
    },
}


class GeoThresholdManager:
    """地理位置阈值管理器 V2"""
    
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
            'cdn_nodes': 0,
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
        
        # 1. 检查是否是CDN节点
        is_cdn = False
        cdn_multiplier = 1.0
        for special_type, config in SPECIAL_KEYWORDS.items():
            if special_type == 'cdn':
                for keyword in config['keywords']:
                    if keyword.lower() in node_name_clean.lower() or keyword in node_name_clean:
                        is_cdn = True
                        cdn_multiplier = config['multiplier']
                        self.stats['cdn_nodes'] += 1
                        break
        
        # CDN节点使用全局阈值并降低
        if is_cdn:
            final_threshold = int(self.base_threshold * cdn_multiplier)
            return final_threshold, 'CDN节点', 998
        
        # 2. 检查特殊关键词（专线等）
        special_multiplier = 1.0
        special_matched = False
        for special_type, config in SPECIAL_KEYWORDS.items():
            if special_type == 'cdn':
                continue
            for keyword in config['keywords']:
                if keyword.lower() in node_name_clean.lower():
                    special_multiplier = config['multiplier']
                    special_matched = True
                    break
            if special_matched:
                break
        
        # 3. 检查地理位置
        for region_key, region_config in GEO_REGIONS.items():
            for keyword in region_config['keywords']:
                # 简化匹配逻辑：直接包含匹配，不使用单词边界
                # 因为emoji等特殊字符会导致单词边界失效
                if keyword.lower() in node_name_clean.lower():
                    # 计算最终阈值
                    final_threshold = int(
                        region_config['base_threshold'] * 
                        region_config['multiplier'] *
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
        
        # 4. 未匹配到任何地区，使用全局基础阈值
        self.stats['unmatched'] += 1
        return self.base_threshold, '未知地区', 999
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()
    
    def print_stats(self):
        """打印统计信息"""
        print("\n" + "="*60)
        print("地理位置识别统计 (V2修正版)")
        print("="*60)
        print(f"总节点数: {self.stats['total']}")
        print(f"已识别: {self.stats['matched']} ({self.stats['matched']/max(self.stats['total'],1)*100:.1f}%)")
        print(f"未识别: {self.stats['unmatched']} ({self.stats['unmatched']/max(self.stats['total'],1)*100:.1f}%)")
        print(f"CDN节点: {self.stats['cdn_nodes']}")
        
        if self.stats['by_region']:
            print("\n各地区分布:")
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
        # 用户反馈的实际节点
        "法国-104.17.49.161-1A",
        "纽约-104.25.248.157-1A",
        "纽约-198.41.209.150-1B",
        
        # 应该保留的亚洲节点
        "🇭🇰 香港-IPLC-01",
        "香港 HKT BGP",
        "🇯🇵 日本东京 NTT",
        "🇸🇬 新加坡-专线",
        "🇰🇷 韩国首尔 KT",
        "🇮🇳 印度孟买",
        
        # 普通节点
        "🇺🇸 美国洛杉矶 CN2 GIA",
        "美国纽约",
        "🇬🇧 英国伦敦",
        "法国巴黎",
    ]
    
    print("\n节点阈值测试 (V2修正版):")
    print("="*90)
    print(f"{'节点名称':<40s} {'阈值(ms)':<12s} {'地区':<15s} {'说明':<20s}")
    print("="*90)
    
    for node in test_nodes:
        threshold, region, priority = manager.get_threshold(node)
        
        # 判断节点类型
        if '104.' in node or '172.' in node:
            note = "CDN节点(严格)"
        elif any(k in node for k in ['香港', '日本', '新加坡', '韩国', '印度', 'HK', 'JP', 'SG', 'KR', 'IN']):
            note = "亚洲节点(保护)"
        elif any(k in node for k in ['法国', '纽约', 'France', 'New York']):
            note = "欧美节点(适中)"
        else:
            note = ""
        
        print(f"{node:<40s} {threshold:<12d} {region:<15s} {note:<20s}")
    
    manager.print_stats()
    
    # 显示策略说明
    print("\n策略调整说明:")
    print("="*90)
    print("V1版本问题：对亚洲节点使用低阈值 → 在巴西测试时延迟高 → 被误杀")
    print("V2版本修正：对亚洲节点使用高阈值 → 确保优质节点不被过滤")
    print("\n具体阈值分配：")
    print("  🇭🇰 港澳台:      3500ms × 1.4 = 4900ms (最宽松)")
    print("  🇯🇵 日韩新:      3200ms × 1.3 = 4160ms (宽松)")
    print("  🇮🇳 其他亚洲:    3000ms × 1.2 = 3600ms (宽松)")
    print("  🇺🇸 美西:        2200ms × 1.0 = 2200ms (标准)")
    print("  🇺🇸 美东:        2000ms × 0.95 = 1900ms (适中)")
    print("  🇬🇧 欧洲:        1800ms × 0.9 = 1620ms (严格)")
    print("  🌐 CDN节点:      2500ms × 0.8 = 2000ms (较严格)")
    print("  💎 专线加成:     × 1.15 (额外宽松15%)")
    print("="*90)


if __name__ == '__main__':
    test_geo_threshold()

