import streamlit as st
import requests
import time

# ===========================================
# CONFIG - CHANGE BACKEND URL HERE
# ===========================================
BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Product Importer", layout="wide")
st.title("📦 Product Importer Frontend (Streamlit)")


# ===========================================
#  PAGE NAVIGATION
# ===========================================
menu = st.sidebar.selectbox(
    "Navigate",
    ["Upload CSV", "Products", "Webhooks"]
)


# ===========================================
# 1️⃣ UPLOAD CSV PAGE
# ===========================================
if menu == "Upload CSV":
    st.header("📤 Upload CSV for Bulk Import")

    uploaded_file = st.file_uploader("Choose CSV file", type=["csv"])

    if uploaded_file:
        st.success("File selected: " + uploaded_file.name)

    if st.button("Start Import"):
        if not uploaded_file:
            st.error("Please upload a CSV file first.")
            st.stop()

        with st.spinner("Uploading file to backend..."):
            files = {"file": (uploaded_file.name, uploaded_file, "text/csv")}
            try:
                res = requests.post(f"{BACKEND_URL}/upload", files=files)
                res.raise_for_status()
            except Exception as e:
                st.error(f"Upload failed: {str(e)}")
                st.stop()

        task_id = res.json().get("task_id")
        st.info(f"Import started, task ID: {task_id}")

        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        message_placeholder = st.empty()

        # Poll progress
        while True:
            time.sleep(1)
            prog_res = requests.get(f"{BACKEND_URL}/progress/{task_id}")
            if prog_res.status_code != 200:
                st.error("Failed to fetch progress.")
                break

            data = prog_res.json()
            progress = float(data.get("progress", 0))
            status = data.get("status", "")
            message = data.get("message", "")

            progress_bar.progress(min(int(progress), 100))
            status_placeholder.write(f"**Status:** {status}")
            message_placeholder.write(f"**Message:** {message}")

            if status in ["completed", "failed"]:
                break

        if status == "completed":
            st.success("🎉 Import completed successfully!")
        else:
            st.error("❌ Import failed")


# ===========================================
# 2️⃣ PRODUCTS PAGE
# ===========================================
if menu == "Products":
    st.header("📋 Product Management")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_sku = st.text_input("Filter by SKU")
    with col2:
        filter_name = st.text_input("Filter by Name")
    with col3:
        filter_active = st.selectbox("Active?", ["All", "True", "False"])

    params = {"skip": 0, "limit": 50}
    if filter_sku:
        params["sku"] = filter_sku
    if filter_name:
        params["name"] = filter_name
    if filter_active != "All":
        params["active"] = True if filter_active == "True" else False

    # Fetch products
    try:
        res = requests.get(f"{BACKEND_URL}/products", params=params)
        res.raise_for_status()
        products = res.json()
    except Exception as e:
        st.error(f"Error fetching products: {e}")
        st.stop()

    # Display table
    st.subheader("Products List")
    if products:
        st.table(products)
    else:
        st.info("No products found.")

    st.markdown("---")

    # Create product
    st.subheader("➕ Create Product")
    sku = st.text_input("SKU")
    name = st.text_input("Name")
    desc = st.text_area("Description")
    price = st.text_input("Price")
    active = st.checkbox("Active", value=True)

    if st.button("Create Product"):
        payload = {
            "sku": sku,
            "name": name,
            "description": desc,
            "price": price,
            "active": active
        }
        try:
            res = requests.post(f"{BACKEND_URL}/products", json=payload)
            if res.status_code == 200:
                st.success("Product created successfully!")
            else:
                st.error(res.json())
        except Exception as e:
            st.error(str(e))

    st.markdown("---")

    # Update product
    st.subheader("✏️ Update Product by SKU")
    update_sku = st.text_input("Enter SKU to update")
    up_name = st.text_input("New Name", key="upname")
    up_desc = st.text_area("New Description", key="updesc")
    up_price = st.text_input("New Price", key="upprice")
    up_active = st.selectbox("Active?", ["No Change", "True", "False"])

    update_payload = {}
    if up_name:
        update_payload["name"] = up_name
    if up_desc:
        update_payload["description"] = up_desc
    if up_price:
        update_payload["price"] = up_price
    if up_active != "No Change":
        update_payload["active"] = True if up_active == "True" else False

    if st.button("Update Product"):
        try:
            res = requests.put(
                f"{BACKEND_URL}/products/{update_sku}",
                json=update_payload
            )
            if res.status_code == 200:
                st.success("Updated successfully!")
            else:
                st.error(res.json())
        except Exception as e:
            st.error(str(e))

    st.markdown("---")

    # Delete product
    st.subheader("🗑 Delete Product by SKU")
    del_sku = st.text_input("SKU to delete")

    if st.button("Delete"):
        try:
            res = requests.delete(f"{BACKEND_URL}/products/{del_sku}")
            if res.status_code == 204:
                st.success("Deleted successfully!")
            else:
                st.error(res.json())
        except Exception as e:
            st.error(str(e))

    st.markdown("---")

    # Bulk Delete
    st.subheader("🔥 Delete ALL Products")
    if st.button("Delete ALL"):
        try:
            res = requests.delete(f"{BACKEND_URL}/products?confirm=true")
            st.success("All products deleted!")
        except Exception as e:
            st.error(str(e))


# ===========================================
# 3️⃣ WEBHOOK PAGE
# ===========================================
if menu == "Webhooks":
    st.header("🔔 Webhook Management")

    # List Webhooks
    st.subheader("Webhook List")
    try:
        res = requests.get(f"{BACKEND_URL}/webhooks")
        hooks = res.json()
        st.table(hooks)
    except:
        st.error("Error fetching webhooks")

    st.markdown("---")

    # Add webhook
    st.subheader("➕ Add Webhook")
    wh_url = st.text_input("Webhook URL")
    wh_event = st.text_input("Event (e.g., product_imported)")

    if st.button("Add Webhook"):
        payload = {"url": wh_url, "event": wh_event, "enabled": True}
        try:
            res = requests.post(f"{BACKEND_URL}/webhooks", json=payload)
            st.success("Webhook added!")
        except Exception as e:
            st.error(str(e))

    st.markdown("---")

    # Test webhook
    st.subheader("🧪 Test Webhook")
    test_id = st.number_input("Webhook ID to test", min_value=1, step=1)

    if st.button("Send Test Event"):
        try:
            res = requests.post(f"{BACKEND_URL}/webhooks/{test_id}/test")
            st.json(res.json())
        except Exception as e:
            st.error(str(e))

    st.markdown("---")

    # Delete webhook
    st.subheader("🗑 Delete Webhook")
    del_id = st.number_input("Webhook ID to delete", min_value=1, step=1, key="delhook")

    if st.button("Delete Webhook"):
        try:
            res = requests.delete(f"{BACKEND_URL}/webhooks/{del_id}")
            st.success("Webhook deleted!")
        except Exception as e:
            st.error(str(e))
