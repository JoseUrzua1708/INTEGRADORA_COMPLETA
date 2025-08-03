// Funciones específicas para administradores

function generateAdminCode() {
  if (confirm("¿Generar un nuevo código de administrador?")) {
    fetch("/api/generate_admin_code", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        rol_id: 2, // Admin
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification(`Código generado: ${data.codigo}`, "success")
          // Copiar al portapapeles
          copyToClipboard(data.codigo)
          // Recargar página para mostrar el nuevo código
          setTimeout(() => {
            location.reload()
          }, 2000)
        } else {
          showNotification("Error al generar código", "error")
        }
      })
      .catch((error) => {
        console.error("Error:", error)
        showNotification("Error de conexión", "error")
      })
  }
}

function copyToClipboard(text) {
  navigator.clipboard
    .writeText(text)
    .then(() => {
      showNotification("Código copiado al portapapeles", "info")
    })
    .catch((err) => {
      console.error("Error al copiar:", err)
      // Fallback para navegadores que no soportan clipboard API
      const textArea = document.createElement("textarea")
      textArea.value = text
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand("copy")
      document.body.removeChild(textArea)
      showNotification("Código copiado al portapapeles", "info")
    })
}

function editUser(userId) {
  // Implementar edición de usuario
  alert(`Función de editar usuario ${userId} próximamente`)
}

function showNotification(message, type = "success") {
  // Crear elemento de notificación
  const notification = document.createElement("div")
  notification.className = "flash-message"
  notification.textContent = message

  if (type === "error") {
    notification.style.background = "#e74c3c"
  } else if (type === "info") {
    notification.style.background = "#3498db"
  }

  // Agregar a contenedor de mensajes
  let container = document.querySelector(".flash-messages")
  if (!container) {
    container = document.createElement("div")
    container.className = "flash-messages"
    document.body.appendChild(container)
  }

  container.appendChild(notification)

  // Remover después de 3 segundos
  setTimeout(() => {
    notification.remove()
  }, 3000)
}
