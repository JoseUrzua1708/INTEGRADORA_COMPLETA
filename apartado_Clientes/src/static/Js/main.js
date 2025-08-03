// Variables globales
const cart = []

// Inicializar cuando el DOM esté listo
document.addEventListener("DOMContentLoaded", () => {
  initializePOS()
})

function initializePOS() {
  // Verificar si el usuario está logueado
  const isLoggedIn = document.querySelector(".order-panel .order-header") !== null

  // Solo agregar event listeners si está logueado
  if (isLoggedIn) {
    // Agregar event listeners a los items del menú
    const menuItems = document.querySelectorAll(".menu-item:not(.menu-item-disabled)")
    menuItems.forEach((item) => {
      item.addEventListener("click", function () {
        const itemId = this.dataset.id
        const itemName = this.dataset.name
        const itemPrice = Number.parseFloat(this.dataset.price)

        addToCart(itemId, itemName, itemPrice)
      })
    })

    // Cargar carrito inicial
    loadCart()
  }

  // Agregar event listener al buscador
  const searchInput = document.getElementById("searchInput")
  if (searchInput) {
    searchInput.addEventListener("input", function () {
      filterMenuItems(this.value)
    })
  }

  // Agregar event listeners a los filtros de categoría
  const categoryBtns = document.querySelectorAll(".category-btn")
  categoryBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      // Remover clase active de todos los botones
      categoryBtns.forEach((b) => b.classList.remove("active"))
      // Agregar clase active al botón clickeado
      this.classList.add("active")

      const category = this.dataset.category
      filterByCategory(category)
    })
  })

  // Event listeners para filtros de pedidos
  const filterBtns = document.querySelectorAll(".filter-btn")
  filterBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      filterBtns.forEach((b) => b.classList.remove("active"))
      this.classList.add("active")

      const status = this.dataset.status
      filterOrders(status)
    })
  })

  // Event listeners para métodos de pago
  const paymentBtns = document.querySelectorAll(".payment-btn")
  paymentBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      paymentBtns.forEach((b) => b.classList.remove("active"))
      this.classList.add("active")
    })
  })

  // Event listener para formulario de agregar mesa
  const addTableForm = document.getElementById("addTableForm")
  if (addTableForm) {
    addTableForm.addEventListener("submit", (e) => {
      e.preventDefault()
      submitNewTable()
    })
  }

  // Event listener para formulario de agregar producto
  const addItemForm = document.getElementById("addItemForm")
  if (addItemForm) {
    addItemForm.addEventListener("submit", (e) => {
      e.preventDefault()
      submitNewItem()
    })
  }
}

// Función para mostrar mensaje cuando se requiere login
function requireLogin() {
  alert("Debes iniciar sesión para usar esta función")
  window.location.href = "/login"
}

// Mejorar la función addToCart para manejar mejor los errores
function addToCart(itemId, itemName, itemPrice) {
  fetch("/api/add_to_order", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      item_id: Number.parseInt(itemId),
      quantity: 1,
    }),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return response.json()
    })
    .then((data) => {
      if (data.success) {
        loadCart()
        showNotification("Producto agregado al pedido")
      } else {
        showNotification(data.error || "Error al agregar producto", "error")
      }
    })
    .catch((error) => {
      console.error("Error:", error)
      showNotification("Error de conexión al agregar producto", "error")
    })
}

function loadCart() {
  fetch("/api/get_cart")
    .then((response) => response.json())
    .then((data) => {
      if (data.cart) {
        updateCartDisplay(data.cart, data.subtotal, data.tax, data.total)
      }
    })
    .catch((error) => {
      console.error("Error loading cart:", error)
    })
}

function updateCartDisplay(cartItems, subtotal, tax, total) {
  const orderItemsContainer = document.getElementById("orderItems")
  const subtotalElement = document.getElementById("subtotal")
  const serviceChargeElement = document.getElementById("serviceCharge")
  const totalElement = document.getElementById("total")

  if (!orderItemsContainer) return

  // Limpiar contenedor
  orderItemsContainer.innerHTML = ""

  // Agregar items al carrito
console.log(cartItems); 
cartItems.forEach((item) => {
    const orderItem = document.createElement("div");
    orderItem.className = "order-item";
    orderItem.innerHTML = `
        <div class="item-image-small">
            <img src="${item.Imagen_URL}" height="50" width="50" alt="${item.name}">
        </div>
        <div class="item-details">
            <div class="item-name">${item.name}</div>
            <div class="item-price">$${item.price.toFixed(2)}</div>
        </div>
        <div class="quantity-controls">
            <button class="quantity-btn" onclick="updateQuantity(${item.id}, ${item.quantity - 1})">-</button>
            <span class="quantity">${item.quantity}</span>
            <button class="quantity-btn" onclick="updateQuantity(${item.id}, ${item.quantity + 1})">+</button>
        </div>
    `;
    orderItemsContainer.appendChild(orderItem);
});

  // Actualizar totales
  if (subtotalElement) subtotalElement.textContent = `$${subtotal.toFixed(2)}`
  if (serviceChargeElement) serviceChargeElement.textContent = `$${tax.toFixed(2)}`
  if (totalElement) totalElement.textContent = `$${total.toFixed(2)}`
}

function updateQuantity(itemId, newQuantity) {
  fetch("/api/update_cart_item", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      item_id: itemId,
      quantity: newQuantity,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        loadCart()
      }
    })
    .catch((error) => {
      console.error("Error:", error)
    })
}

// Modificar la función placeOrder existente
function placeOrder() {
  // Verificar que hay items en el carrito
  const orderItems = document.getElementById("orderItems")
  if (!orderItems || orderItems.children.length === 0) {
    showNotification("El carrito está vacío", "error")
    return
  }

  // Deshabilitar botón para evitar doble envío
  const sendBtn = document.querySelector(".btn-send")
  if (sendBtn) {
    sendBtn.disabled = true
    sendBtn.textContent = "ENVIANDO..."
  }

  fetch("/api/place_order", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return response.json()
    })
    .then((data) => {
      if (data.success) {
        showNotification(`¡Pedido enviado! Código: ${data.order_code}`, "success")
        showNotification("Ahora procede al pago", "info")

        // Mostrar botón de pago y ocultar botón de enviar
        const paymentBtn = document.getElementById("paymentBtn")
        if (paymentBtn) {
          paymentBtn.style.display = "block"
        }
        if (sendBtn) {
          sendBtn.style.display = "none"
        }

        // Generar nuevo número de orden
        const orderNumberElement = document.getElementById("orderNumber")
        if (orderNumberElement) {
          orderNumberElement.textContent = Math.floor(Math.random() * 90000000) + 10000000
        }
      } else {
        showNotification(data.error || "Error al enviar pedido", "error")
      }
    })
    .catch((error) => {
      console.error("Error:", error)
      showNotification("Error de conexión al enviar pedido", "error")
    })
    .finally(() => {
      // Rehabilitar botón
      if (sendBtn) {
        sendBtn.disabled = false
        sendBtn.textContent = "ENVIAR PEDIDO"
      }
    })
}

// Agregar nueva función para ir a pagar
function goToPayment() {
  window.location.href = "/payment"
}

// Modificar clearOrder para resetear los botones
function clearOrder() {
  if (confirm("¿Estás seguro de que quieres cancelar el pedido?")) {
    fetch("/api/clear_cart", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          loadCart()
          showNotification("Pedido cancelado")

          // Resetear botones
          const sendBtn = document.querySelector(".btn-send")
          const paymentBtn = document.getElementById("paymentBtn")

          if (sendBtn) {
            sendBtn.style.display = "block"
            sendBtn.disabled = false
            sendBtn.textContent = "ENVIAR PEDIDO"
          }

          if (paymentBtn) {
            paymentBtn.style.display = "none"
          }
        }
      })
      .catch((error) => {
        console.error("Error:", error)
      })
  }
}

function filterMenuItems(searchTerm) {
  const menuItems = document.querySelectorAll(".menu-item")
  const term = searchTerm.toLowerCase()

  menuItems.forEach((item) => {
    const itemName = item.dataset.name.toLowerCase()
    if (itemName.includes(term)) {
      item.style.display = "block"
    } else {
      item.style.display = "none"
    }
  })
}

function filterByCategory(category) {
    const menuItems = document.querySelectorAll(".menu-item")

    menuItems.forEach((item) => {
        // Asegúrate de que el atributo data-category exista en tu HTML
        const itemCategory = item.dataset.category

        if (category === "all" || itemCategory === category) {
            item.style.display = "block"
        } else {
            item.style.display = "none"
        }
    })
}

function filterOrders(status) {
  const orderCards = document.querySelectorAll(".order-card")

  orderCards.forEach((card) => {
    if (status === "all") {
      card.style.display = "block"
    } else {
      const cardStatus = card.dataset.status
      if (cardStatus === status) {
        card.style.display = "block"
      } else {
        card.style.display = "none"
      }
    }
  })
}

function updateOrderStatus(orderId, newStatus) {
  fetch("/api/update_order_status", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      order_id: orderId,
      status: newStatus,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showNotification("Estado del pedido actualizado")
        // Actualizar la página para reflejar los cambios
        setTimeout(() => {
          location.reload()
        }, 1000)
      } else {
        showNotification("Error al actualizar el estado", "error")
      }
    })
    .catch((error) => {
      console.error("Error:", error)
      showNotification("Error de conexión", "error")
    })
}

function processPayment() {
  const selectedMethod = document.querySelector(".payment-btn.active")
  if (!selectedMethod) {
    showNotification("Selecciona un método de pago", "error")
    return
  }

  const method = selectedMethod.dataset.method

  // Simular procesamiento de pago
  showNotification("Procesando pago...", "info")

  setTimeout(() => {
    fetch("/api/place_order", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification(`¡Pago procesado exitosamente con ${method}!`, "success")
          setTimeout(() => {
            window.location.href = "/pos"
          }, 2000)
        } else {
          showNotification("Error al procesar el pago", "error")
        }
      })
      .catch((error) => {
        console.error("Error:", error)
        showNotification("Error de conexión", "error")
      })
  }, 2000)
}

// Funciones para administradores
function showAddTableModal() {
  const modal = document.getElementById("addTableModal")
  if (modal) {
    modal.style.display = "block"
  }
}

function closeAddTableModal() {
  const modal = document.getElementById("addTableModal")
  if (modal) {
    modal.style.display = "none"
  }
}

function showAddItemModal() {
  const modal = document.getElementById("addItemModal")
  if (modal) {
    modal.style.display = "block"
  }
}

function closeAddItemModal() {
  const modal = document.getElementById("addItemModal")
  if (modal) {
    modal.style.display = "none"
  }
}

function submitNewTable() {
  const form = document.getElementById("addTableForm")
  const formData = new FormData(form)

  const tableData = {
    sucursal_id: formData.get("sucursal_id"),
    numero_mesa: formData.get("numero_mesa"),
    capacidad: formData.get("capacidad"),
    ubicacion: formData.get("ubicacion"),
  }

  fetch("/api/add_table", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(tableData),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showNotification("Mesa agregada exitosamente")
        closeAddTableModal()
        setTimeout(() => {
          location.reload()
        }, 1000)
      } else {
        showNotification("Error al agregar mesa", "error")
      }
    })
    .catch((error) => {
      console.error("Error:", error)
      showNotification("Error de conexión", "error")
    })
}

function submitNewItem() {
  const form = document.getElementById("addItemForm")
  const formData = new FormData(form)

  const itemData = {
    nombre: formData.get("nombre"),
    descripcion: formData.get("descripcion"),
    precio: Number.parseFloat(formData.get("precio")),
    categoria_id: Number.parseInt(formData.get("categoria_id")),
  }

  fetch("/api/add_menu_item", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(itemData),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showNotification("Producto agregado exitosamente")
        closeAddItemModal()
        setTimeout(() => {
          location.reload()
        }, 1000)
      } else {
        showNotification("Error al agregar producto", "error")
      }
    })
    .catch((error) => {
      console.error("Error:", error)
      showNotification("Error de conexión", "error")
    })
}

// Funciones para clientes
function cancelOrder(orderId) {
  if (confirm("¿Estás seguro de que quieres cancelar este pedido?")) {
    fetch("/api/update_order_status", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        order_id: orderId,
        status: "Cancelado",
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification("Pedido cancelado exitosamente")
          setTimeout(() => {
            location.reload()
          }, 1000)
        } else {
          showNotification("Error al cancelar pedido", "error")
        }
      })
      .catch((error) => {
        console.error("Error:", error)
        showNotification("Error de conexión", "error")
      })
  }
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

// Función para depurar problemas de carga de imágenes
function logImageError(imageUrl, itemName) {
  console.error(`Error al cargar imagen: ${imageUrl} para el producto: ${itemName}`)
}

// Función para verificar todas las imágenes del menú
function checkMenuImages() {
  const menuItems = document.querySelectorAll(".menu-item .item-image img")
  console.log(`Verificando ${menuItems.length} imágenes del menú...`)

  menuItems.forEach((img, index) => {
    const itemName = img.closest(".menu-item").querySelector(".item-info h3").textContent
    console.log(`[${index + 1}/${menuItems.length}] Imagen: ${img.src} - Producto: ${itemName}`)

    // Verificar si la imagen ya ha fallado
    if (img.naturalWidth === 0) {
      logImageError(img.src, itemName)
    }
  })
}

// Auto-remover mensajes flash después de 5 segundos
document.addEventListener("DOMContentLoaded", () => {
  const flashMessages = document.querySelectorAll(".flash-message")
  flashMessages.forEach((message) => {
    setTimeout(() => {
      message.remove()
    }, 5000)
  })

  // Verificar imágenes después de un breve retraso
  setTimeout(checkMenuImages, 2000)
})

// Cerrar modal al hacer clic fuera de él
window.onclick = (event) => {
  const addTableModal = document.getElementById("addTableModal")
  const addItemModal = document.getElementById("addItemModal")

  if (event.target === addTableModal) {
    closeAddTableModal()
  }
  if (event.target === addItemModal) {
    closeAddItemModal()
  }
}

// Agregar estas nuevas funciones al final del archivo

// Funciones para categorías
function showAddCategoryModal() {
  const modal = document.getElementById("addCategoryModal")
  if (modal) {
    modal.style.display = "block"
  }
}

function closeAddCategoryModal() {
  const modal = document.getElementById("addCategoryModal")
  if (modal) {
    modal.style.display = "none"
  }
}

// Funciones para sucursales (solo dueño)
function showAddSucursalModal() {
  const modal = document.getElementById("addSucursalModal")
  if (modal) {
    modal.style.display = "block"
  }
}

function closeAddSucursalModal() {
  const modal = document.getElementById("addSucursalModal")
  if (modal) {
    modal.style.display = "none"
  }
}

// Event listeners para los nuevos formularios
document.addEventListener("DOMContentLoaded", () => {
  // Event listener para formulario de agregar categoría
  const addCategoryForm = document.getElementById("addCategoryForm")
  if (addCategoryForm) {
    addCategoryForm.addEventListener("submit", (e) => {
      e.preventDefault()
      submitNewCategory()
    })
  }

  // Event listener para formulario de agregar sucursal
  const addSucursalForm = document.getElementById("addSucursalForm")
  if (addSucursalForm) {
    addSucursalForm.addEventListener("submit", (e) => {
      e.preventDefault()
      submitNewSucursal()
    })
  }
})

function submitNewCategory() {
  const form = document.getElementById("addCategoryForm")
  const formData = new FormData(form)

  const categoryData = {
    nombre: formData.get("nombre"),
    descripcion: formData.get("descripcion"),
  }

  fetch("/api/add_category", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(categoryData),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showNotification("Categoría agregada exitosamente")
        closeAddCategoryModal()
        setTimeout(() => {
          location.reload()
        }, 1000)
      } else {
        showNotification("Error al agregar categoría", "error")
      }
    })
    .catch((error) => {
      console.error("Error:", error)
      showNotification("Error de conexión", "error")
    })
}

// Agregar función para manejar errores de sucursal
function submitNewSucursal() {
  const form = document.getElementById("addSucursalForm")
  const formData = new FormData(form)

  // Validar campos requeridos
  const nombre = formData.get("nombre")
  const direccion = formData.get("direccion")
  const telefono = formData.get("telefono")

  if (!nombre || !direccion || !telefono) {
    showNotification("Todos los campos son requeridos", "error")
    return
  }

  const sucursalData = {
    nombre: nombre,
    direccion: direccion,
    telefono: telefono,
  }

  fetch("/api/add_sucursal", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(sucursalData),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return response.json()
    })
    .then((data) => {
      if (data.success) {
        showNotification("Sucursal agregada exitosamente")
        closeAddSucursalModal()
        form.reset() // Limpiar formulario
        setTimeout(() => {
          location.reload()
        }, 1000)
      } else {
        showNotification(data.error || "Error al agregar sucursal", "error")
      }
    })
    .catch((error) => {
      console.error("Error:", error)
      showNotification("Error de conexión al agregar sucursal", "error")
    })
}

function deleteOrder(orderId) {
  if (confirm("¿Estás seguro de que quieres eliminar este pedido? Esta acción no se puede deshacer.")) {
    fetch("/api/delete_order", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        order_id: orderId,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification("Pedido eliminado exitosamente")
          setTimeout(() => {
            location.reload()
          }, 1000)
        } else {
          showNotification("Error al eliminar pedido", "error")
        }
      })
      .catch((error) => {
        console.error("Error:", error)
        showNotification("Error de conexión", "error")
      })
  }
}

// Actualizar la función de cerrar modales
window.onclick = (event) => {
  const addTableModal = document.getElementById("addTableModal")
  const addItemModal = document.getElementById("addItemModal")
  const addCategoryModal = document.getElementById("addCategoryModal")
  const addSucursalModal = document.getElementById("addSucursalModal")

  if (event.target === addTableModal) {
    closeAddTableModal()
  }
  if (event.target === addItemModal) {
    closeAddItemModal()
  }
  if (event.target === addCategoryModal) {
    closeAddCategoryModal()
  }
  if (event.target === addSucursalModal) {
    closeAddSucursalModal()
  }
}
