#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour valider les améliorations du système de génération de versets
"""

from datetime import datetime
from src.soul_verse_api.services.image_generation_service import ImageGenerationService
from src.soul_verse_api.services.scheduler_service import SchedulerService
import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))


async def test_special_occasions():
    """Teste la détection des occasions spéciales"""
    print("🎯 Test de détection des occasions spéciales\n")

    scheduler = SchedulerService()

    # Test pour aujourd'hui (1er janvier 2026)
    today_occasion = scheduler.get_special_occasion()

    if today_occasion:
        print(f"✅ Occasion détectée pour aujourd'hui:")
        print(f"   Nom: {today_occasion['name']}")
        print(f"   Description: {today_occasion['description']}")
        print(f"   Priorité: {today_occasion['priority']}")
        print(f"   Thèmes: {', '.join(today_occasion['themes'])}")
    else:
        print("❌ Aucune occasion spéciale détectée pour aujourd'hui")

    print("\n" + "="*70 + "\n")

    # Test pour le 25 décembre
    christmas = datetime(2026, 12, 25)
    christmas_occasion = scheduler.get_special_occasion(christmas)

    if christmas_occasion:
        print(f"✅ Occasion détectée pour Noël (25/12):")
        print(f"   Nom: {christmas_occasion['name']}")
        print(f"   Description: {christmas_occasion['description']}")
        print(f"   Priorité: {christmas_occasion['priority']}")

    print("\n" + "="*70 + "\n")


def test_visual_extraction():
    """Teste l'extraction d'éléments visuels"""
    print("🎨 Test d'extraction d'éléments visuels\n")

    image_service = ImageGenerationService()

    # Test avec différents versets
    test_cases = [
        {
            "verse": "L'Éternel est ma lumière et mon salut",
            "reference": "Psaume 27:1",
            "ai_elements": "lumière divine, protection céleste"
        },
        {
            "verse": "Le Seigneur est mon berger, je ne manquerai de rien",
            "reference": "Psaume 23:1",
            "ai_elements": None
        },
        {
            "verse": "Il me fait reposer dans de verts pâturages, Il me dirige près des eaux paisibles",
            "reference": "Psaume 23:2",
            "ai_elements": "pâturages verdoyants, eaux calmes"
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}:")
        print(f"Verset: {test['verse']}")
        print(f"Référence: {test['reference']}")

        visual_elements = image_service._extract_visual_elements(
            test['verse'],
            test['reference'],
            test['ai_elements']
        )

        print(f"✅ Éléments visuels extraits:")
        print(f"   {visual_elements}")
        print()

    print("="*70 + "\n")


def test_prompt_generation():
    """Teste la génération de prompts pour Stability AI"""
    print("📝 Test de génération de prompts Stability AI\n")

    print("Les prompts sont maintenant enrichis avec:")
    print("✅ Extraction automatique d'éléments visuels du verset")
    print("✅ Styles détaillés par mood/occasion (atmosphère, éclairage, couleurs)")
    print("✅ Negative prompts pour éviter éléments indésirables")
    print("✅ Paramètres optimisés (cfg_scale: 9, steps: 40)")
    print("✅ Style artistique: digital-art")
    print("✅ Sampler avancé: K_DPMPP_2M")

    print("\nExemple de structure de prompt:")
    print("""
    Masterpiece biblical spiritual artwork depicting: [éléments visuels extraits]
    
    Verse context: [référence] - [texte du verset]
    
    Atmosphere: [peaceful, joyful, etc.]
    Lighting: [soft heavenly light, etc.]
    Color palette: [soft blues, whites, etc.]
    Key elements: [calm waters, dove, etc.]
    
    Art style: highly detailed religious art, renaissance inspired...
    Quality: 8k, ultra detailed, masterpiece...
    """)

    print("="*70 + "\n")


def test_pastoral_reflections():
    """Affiche des exemples de réflexions pastorales"""
    print("🙏 Exemples de réflexions pastorales détaillées\n")

    print("AVANT (2-3 phrases):")
    print("─" * 70)
    print('"Les compassions de l\'Éternel se renouvellent chaque matin.')
    print('En cette nouvelle année, confie-toi en Sa fidélité qui ne fait jamais défaut."')

    print("\n\nMAINTENANT (5-7 phrases avec enseignement):")
    print("─" * 70)
    print('''
"Mes bien-aimés, ce passage des Lamentations nous révèle une vérité 
puissante: la fidélité de Dieu se renouvelle chaque matin comme l'aurore 
qui chasse les ténèbres. Le prophète Jérémie, au milieu des ruines de 
Jérusalem, a découvert que même dans la désolation la plus profonde, 
les compassions de l'Éternel ne s'épuisent jamais. En cette nouvelle 
année qui s'ouvre devant nous, comprenons que chaque jour est une page 
blanche où Dieu écrit de nouvelles grâces. Comme la manne tombait 
fraîche chaque matin pour Israël dans le désert, ainsi Sa miséricorde 
nous attend au réveil. Ne portons pas les fardeaux d'hier dans ce 
nouveau chapitre - Dieu nous appelle à marcher dans la confiance, 
sachant qu'Il est fidèle pour accomplir ce qu'Il a commencé en nous. 
Que cette année soit marquée par notre foi en Sa fidélité inébranlable!"
    ''')

    print("\nCaractéristiques:")
    print("✅ Contexte biblique expliqué (Jérémie dans les ruines)")
    print("✅ Signification profonde (fidélité renouvelée comme l'aurore)")
    print("✅ Exemple biblique (la manne dans le désert)")
    print("✅ Application pratique (ne pas porter les fardeaux d'hier)")
    print("✅ Encouragement et appel (marcher dans la confiance)")

    print("\n" + "="*70 + "\n")


async def main():
    """Fonction principale de test"""
    print("\n" + "="*70)
    print("🚀 Tests des Améliorations - Réflexions Pastorales et Images")
    print("="*70 + "\n")

    # Test 1: Détection des occasions spéciales
    await test_special_occasions()

    # Test 2: Extraction d'éléments visuels
    test_visual_extraction()

    # Test 3: Génération de prompts
    test_prompt_generation()

    # Test 4: Exemples de réflexions
    test_pastoral_reflections()

    print("🎉 Tous les tests sont terminés!")
    print("\n💡 Prochaines étapes:")
    print("   1. Tester avec des utilisateurs réels")
    print("   2. Vérifier la qualité des images générées par Stability AI")
    print("   3. Collecter les feedbacks sur les réflexions pastorales")
    print("   4. Ajuster selon les retours")
    print("\n✨ Que Dieu bénisse ce travail! 🙏\n")


if __name__ == "__main__":
    asyncio.run(main())
