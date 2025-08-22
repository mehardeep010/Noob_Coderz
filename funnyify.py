#!/usr/bin/env python3
"""
Enhanced PDF Funnyify Script
Transforms boring PDFs into hilarious masterpieces with cats, emojis, and AI-powered humor!

Usage: python funnyify.py input.pdf output.pdf [options]
"""

import os
import sys
import random
import re
import logging
import requests
import argparse
import tempfile
from io import BytesIO
from typing import List, Dict, Optional, Tuple

try:
    import pdfplumber
    from fpdf import FPDF
    from PIL import Image
except ImportError as e:
    print(f"❌ Missing required package: {e}")
    print("📦 Please install with: pip install pdfplumber fpdf2 Pillow")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class EnhancedPDFFunnyify:
    """Enhanced PDF transformation with multiple humor styles and features"""
    
    # Humor configuration
    HUMOR_STYLES = {
        'mild': {
            'emoji_frequency': 0.1,
            'cat_frequency': 5,
            'text_replacement_chance': 0.2,
            'chaos_level': 1
        },
        'spicy': {
            'emoji_frequency': 0.3,
            'cat_frequency': 3,
            'text_replacement_chance': 0.4,
            'chaos_level': 2
        },
        'chaotic': {
            'emoji_frequency': 0.5,
            'cat_frequency': 2,
            'text_replacement_chance': 0.6,
            'chaos_level': 3
        }
    }
    
    # Emoji collections by category
    EMOJIS = {
        'faces': ['😂', '😹', '🤣', '😊', '😎', '🤪', '😜', '🥳', '😇', '🤠'],
        'animals': ['🐱', '🐶', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐨', '🐸'],
        'food': ['🍕', '🍔', '🌭', '🍟', '🍿', '🧀', '🍪', '🍩', '🍰', '🎂'],
        'misc': ['🎉', '✨', '🌟', '⭐', '🎊', '🎈', '🎁', '🏆', '💎', '🔥']
    }
    
    # Funny text replacements
    TEXT_REPLACEMENTS = {
        'mild': {
            'important': 'super duper important 🌟',
            'significant': 'mega significant ✨',
            'analysis': 'fancy detective work 🔍',
            'conclusion': 'the big reveal 🎭',
            'therefore': 'so basically 🤷‍♂️',
            'however': 'but wait, there\'s more! 📢',
            'furthermore': 'and another thing... 🎪',
            'accordingly': 'so here we go 🚀'
        },
        'spicy': {
            'meeting': 'awkward gathering of humans 🤝',
            'presentation': 'fancy slideshow extravaganza 📊',
            'deadline': 'panic-inducing date 📅',
            'budget': 'imaginary numbers game 💰',
            'stakeholder': 'important person who asks questions 👔',
            'synergy': 'magical teamwork fairy dust ✨',
            'optimization': 'making stuff less broken 🔧',
            'implementation': 'actually doing the thing 🛠️'
        },
        'chaotic': {
            'corporation': 'fancy business thingy 🏢',
            'executive': 'person in expensive suit 👔',
            'quarterly': 'every three moon cycles 🌙',
            'revenue': 'money magic 💸',
            'strategic': 'really really planned out 🎯',
            'innovative': 'shiny and new 🦄',
            'disruptive': 'chaos-bringing 🌪️',
            'paradigm': 'fancy word for way of thinking 🧠'
        }
    }
    
    # Cat image URLs (placeholder - in real use, you'd want local images or a reliable API)
    CAT_IMAGES = [
        "https://placekitten.com/200/200",
        "https://placekitten.com/250/200",
        "https://placekitten.com/200/250",
        "https://placekitten.com/300/200",
        "https://placekitten.com/200/300"
    ]
    
    def __init__(self, style: str = 'mild', enable_emojis: bool = True, 
                 enable_cats: bool = True, cat_frequency: int = 3,
                 enable_ai: bool = False, api_key: str = None):
        """Initialize the PDF funnyifier"""
        self.style = style
        self.config = self.HUMOR_STYLES.get(style, self.HUMOR_STYLES['mild'])
        self.enable_emojis = enable_emojis
        self.enable_cats = enable_cats
        self.cat_frequency = cat_frequency
        self.enable_ai = enable_ai
        self.api_key = api_key
        
        # Override cat frequency if specified
        if cat_frequency:
            self.config['cat_frequency'] = cat_frequency
            
        logger.info(f"🎭 Initialized funnyifier with style: {style}")
        logger.info(f"🎨 Config: {self.config}")
        
    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Extract text and structure from PDF"""
        logger.info("📖 Extracting text from PDF...")
        
        pages_data = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    logger.info(f"📄 Processing page {i+1}/{len(pdf.pages)}")
                    
                    text = page.extract_text()
                    if text:
                        # Split into paragraphs
                        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                        
                        pages_data.append({
                            'page_num': i + 1,
                            'paragraphs': paragraphs,
                            'original_text': text
                        })
                        
            logger.info(f"✅ Extracted text from {len(pages_data)} pages")
            return pages_data
            
        except Exception as e:
            logger.error(f"❌ Error extracting text: {e}")
            return []
    
    def add_emojis_to_text(self, text: str) -> str:
        """Add random emojis to text based on frequency setting"""
        if not self.enable_emojis or not text:
            return text
            
        words = text.split()
        emoji_frequency = self.config['emoji_frequency']
        
        # Choose emoji category based on chaos level
        if self.config['chaos_level'] == 1:
            emoji_pool = self.EMOJIS['faces']
        elif self.config['chaos_level'] == 2:
            emoji_pool = self.EMOJIS['faces'] + self.EMOJIS['misc']
        else:
            emoji_pool = sum(self.EMOJIS.values(), [])
        
        result_words = []
        for word in words:
            result_words.append(word)
            
            # Maybe add an emoji after this word
            if random.random() < emoji_frequency:
                emoji = random.choice(emoji_pool)
                result_words.append(emoji)
                
        return ' '.join(result_words)
    
    def replace_funny_words(self, text: str) -> str:
        """Replace boring words with funny alternatives"""
        if not text:
            return text
            
        replacements = self.TEXT_REPLACEMENTS.get(self.style, {})
        replacement_chance = self.config['text_replacement_chance']
        
        for boring_word, funny_word in replacements.items():
            if random.random() < replacement_chance:
                # Case-insensitive replacement
                pattern = re.compile(re.escape(boring_word), re.IGNORECASE)
                text = pattern.sub(funny_word, text)
                
        return text
    
    def download_cat_image(self, url: str, timeout: int = 10) -> Optional[Image.Image]:
        """Download a cat image from URL"""
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            img = Image.open(BytesIO(response.content))
            # Resize to reasonable size
            img.thumbnail((200, 200), Image.Resampling.LANCZOS)
            return img
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to download cat image: {e}")
            return None
    
    def create_cat_placeholder(self) -> Image.Image:
        """Create a placeholder cat image if download fails"""
        img = Image.new('RGB', (200, 200), color='lightgray')
        # In a real implementation, you'd draw a simple cat or use a local fallback
        return img
    
    def process_with_ai(self, text: str) -> str:
        """Process text with AI to make it funny (placeholder - requires OpenAI setup)"""
        if not self.enable_ai or not self.api_key:
            return text
            
        try:
            # This is a placeholder - you'd implement actual OpenAI API calls here
            logger.info("🤖 AI processing not fully implemented in this demo")
            return self.add_funny_prefix(text)
            
        except Exception as e:
            logger.warning(f"⚠️ AI processing failed: {e}")
            return text
    
    def add_funny_prefix(self, text: str) -> str:
        """Add a funny prefix to paragraphs"""
        prefixes = {
            'mild': ["Fun fact:", "Here's the thing:", "Guess what?", "Plot twist:"],
            'spicy': ["Breaking news:", "URGENT UPDATE:", "Scientists hate this:", "You won't believe this:"],
            'chaotic': ["BREAKING: Local PDF declares:", "CHAOS REPORT:", "EMERGENCY BULLETIN:", "DRAMATIC PLOT TWIST:"]
        }
        
        style_prefixes = prefixes.get(self.style, prefixes['mild'])
        
        if random.random() < 0.3:  # 30% chance to add prefix
            prefix = random.choice(style_prefixes)
            return f"{prefix} {text
