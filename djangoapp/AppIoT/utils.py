def check_and_notify_adjacent_rooms(room):
    """Verifica le condizioni di una stanza e notifica altre stanze se necessario."""
    
    if room.co2 > 1000:
        print(f"⚠️ CO₂ elevata in {room.name}! Suggerisco stanze alternative...")
        alternative_rooms = room.adjacent_rooms.filter(co2__lt=800).order_by('-bestroom')

        for alt in alternative_rooms:
            print(f"👉 Alternativa consigliata: {alt.name} con CO₂: {alt.co2} ppm")
