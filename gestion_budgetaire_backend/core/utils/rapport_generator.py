def generate_rapport_file(budget, recettes, depenses, commandes, periode, user):
    from io import BytesIO
    from django.core.files.base import ContentFile
    from reportlab.pdfgen import canvas
    from django.utils.timezone import now

    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setTitle(f"Rapport {budget.exercice}")

    # Titres
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, f"RAPPORT FINANCIER - {budget.exercice}")
    p.setFont("Helvetica", 12)
    p.drawString(100, 780, f"Période : {periode}")

    # Infos Budget
    p.drawString(100, 750, f"Montant Total : {budget.montant_total:,} FCFA")
    p.drawString(100, 735, f"Montant Disponible : {budget.montant_disponible:,} FCFA")

    # Recettes
    y = 700
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y, "Recettes :")
    p.setFont("Helvetica", 12)
    for recette in recettes:
        y -= 15
        p.drawString(120, y, f"- {recette.source} ({recette.type}) : {recette.montant:,} FCFA")

    # Dépenses
    y -= 30
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y, "Dépenses validées :")
    p.setFont("Helvetica", 12)
    for depense in depenses:
        y -= 15
        p.drawString(120, y, f"- {depense.type_depense} ({depense.categorie}) : {depense.montant:,} FCFA")

    # Commandes
    y -= 30
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y, "Commandes :")
    p.setFont("Helvetica", 12)
    for commande in commandes:
        y -= 15
        p.drawString(120, y, f"- {commande.designation} (Qté: {commande.quantite}) : {commande.total:,} FCFA")

    # Footer
    y -= 30
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(100, y, f"Généré par : {user.nom} ({user.role}) - {now().strftime('%d/%m/%Y %H:%M')}")

    p.showPage()
    p.save()
    buffer.seek(0)

    fichier_nom = f"rapport_{budget.exercice}_{periode}.pdf"
    return ContentFile(buffer.read(), name=fichier_nom), fichier_nom
