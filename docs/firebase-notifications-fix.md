# Firebase Notifications - Corrections et Documentation

## 📋 Problèmes Résolus

### 1. **Attributs et paramètres inexistants dans firebase_admin.messaging**

**Problème :** Le code utilisait des attributs et paramètres qui n'existent pas dans Firebase Admin SDK v7.x

**Erreurs rencontrées :**
```python
AttributeError: module 'firebase_admin.messaging' has no attribute 'Priority'
AttributeError: module 'firebase_admin.messaging' has no attribute 'Visibility'
AndroidNotification.__init__() got an unexpected keyword argument 'notification_priority'
```

**Solutions appliquées :**

#### ❌ Avant (code incorrect)
```python
# Utilisation d'énumérations inexistantes
notification_priority=messaging.Priority.HIGH
visibility=messaging.Visibility.PUBLIC

# Paramètres invalides dans AndroidNotification
android_config = messaging.AndroidConfig(
    notification=messaging.AndroidNotification(
        notification_priority=messaging.Priority.HIGH,  # ❌ N'existe pas
        visibility=messaging.Visibility.PUBLIC,  # ❌ N'existe pas
    )
)
```

#### ✅ Après (code corrigé)
```python
# Pas de notification_priority ni visibility dans AndroidNotification
android_config = messaging.AndroidConfig(
    priority="high",  # ✅ Priority au niveau AndroidConfig (string)
    notification=messaging.AndroidNotification(
        title=title,
        body=body,
        icon="ic_stat_soulverse",
        color="#4A90E2",
        sound="default",
        channel_id=f"soulverse_{notification_type.value}"
        # ⚠️ Pas de notification_priority ni visibility ici
    )
)
```

### 2. **Utilisation correcte de send_multicast**

**✅ MulticastMessage et send_multicast EXISTENT dans Firebase Admin SDK v7.x**

```python
# ✅ Approche correcte pour envoyer à plusieurs tokens
multicast_message = messaging.MulticastMessage(
    notification=messaging.Notification(title=title, body=body),
    data=data_payload,
    tokens=tokens,  # Liste de tokens
    android=android_config,
    apns=apns_config
)

response = messaging.send_multicast(multicast_message)
```

## 📚 API Firebase Admin SDK v7.x - Référence Correcte

### Méthodes d'envoi disponibles

| Méthode | Usage | Description |
|---------|-------|-------------|
| `messaging.send(message)` | Message unique | Envoie à un seul token/topic |
| `messaging.send_multicast(multicast)` | Envoi groupé | Envoie à plusieurs tokens (max 500) |

### Paramètres INVALIDES pour AndroidNotification

**❌ Ces paramètres n'existent PAS :**
- `notification_priority` - N'existe pas dans AndroidNotification
- `visibility` - N'existe pas dans AndroidNotification

**✅ Paramètres VALIDES pour AndroidNotification :**
- `title` - Titre de la notification
- `body` - Corps de la notification
- `icon` - Icône de l'app (ex: "ic_stat_soulverse")
- `color` - Couleur de l'icône (ex: "#4A90E2")
- `sound` - Son de notification ("default")
- `channel_id` - Canal de notification Android
- `image` - URL de l'image (optionnel)

### Classes et configurations valides

```python
# ✅ Configuration Android
android_config = messaging.AndroidConfig(
    priority="high",  # ✅ Priority ICI (string: "high" ou "normal")
    notification=messaging.AndroidNotification(
        title="Titre",
        body="Message",
        icon="ic_notification",
        color="#RRGGBB",
        sound="default",
        channel_id="channel_name",
        image="https://url-image.jpg"  # optionnel
        # ⚠️ PAS de notification_priority ni visibility ici
    )
)

# ✅ Configuration iOS (APNS)
apns_config = messaging.APNSConfig(
    payload=messaging.APNSPayload(
        aps=messaging.Aps(
            alert=messaging.ApsAlert(
                title="Titre",
                body="Message"
            ),
            sound="default",
            badge=1
        )
    )
)

# ✅ Message avec notification et data
message = messaging.Message(
    notification=messaging.Notification(
        title="Titre",
        body="Message",
        image="https://url-image.jpg"  # optionnel
    ),
    data={
        "key1": "value1",
        "key2": "value2"
    },
    token="FCM_TOKEN",  # ou topic="topic_name"
    android=android_config,
    apns=apns_config
)
```

## 🔧 Configuration Correcte pour SoulVerse

### Envoi à un seul utilisateur
```python
def send_to_token(self, title: str, body: str, token: str, **kwargs):
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data=data_payload,
        token=token,
        android=android_config,
        apns=apns_config
    )
    response = messaging.send(message)
    return True
```

### Envoi à plusieurs utilisateurs (multicast)
```python
def send_to_multiple(self, title: str, body: str, tokens: List[str], **kwargs):
    # ✅ Utiliser MulticastMessage
    multicast_message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data=data_payload,
        tokens=tokens,  # Liste de tokens (max 500)
        android=android_config,
        apns=apns_config
    )
    
    # ✅ Utiliser send_multicast (pas send_all)
    response = messaging.send_multicast(multicast_message)
    
    return {
        "success_count": response.success_count,
        "failure_count": response.failure_count
    }
```

### Envoi à un topic
```python
def send_to_topic(self, title: str, body: str, topic: str, **kwargs):
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data=data_payload,
        topic=topic,  # Au lieu de token
        android=android_config,
        apns=apns_config
    )
    response = messaging.send(message)
    return True
```

## ✅ Checklist de migration

- [x] Retirer `notification_priority` de `AndroidNotification`
- [x] Retirer `visibility` de `AndroidNotification`
- [x] Utiliser `priority="high"` (string) dans `AndroidConfig` uniquement
- [x] Utiliser `messaging.MulticastMessage` pour l'envoi groupé
- [x] Utiliser `messaging.send_multicast()` (PAS `send_all()`)
- [x] Vérifier que tous les paramètres sont des strings
- [x] Priority définie au niveau `AndroidConfig`, pas `AndroidNotification`

## 📖 Ressources

- [Firebase Admin SDK Python Reference](https://firebase.google.com/docs/reference/admin/python/firebase_admin.messaging)
- [FCM HTTP v1 API](https://firebase.google.com/docs/cloud-messaging/send-message)
- [Android Notification Configuration](https://firebase.google.com/docs/cloud-messaging/admin/send-messages#android_specific_fields)

## 🎯 Version actuelle

- **Firebase Admin SDK:** v7.1.0
- **Python:** 3.x
- **Date de correction:** 31 décembre 2025
