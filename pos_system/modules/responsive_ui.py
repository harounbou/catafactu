"""
Responsive UI module for the POS system.
Provides functions to create responsive UI elements for different screen sizes.
"""
import streamlit as st

def get_device_type():
    """
    Detect the device type based on screen width.
    
    Returns:
        str: Device type ('mobile', 'tablet', or 'desktop')
    """
    # Use session state to store the device type
    if 'device_type' not in st.session_state:
        # Default to desktop if we can't detect
        st.session_state.device_type = 'desktop'
        
        # Add JavaScript to detect screen width
        st.markdown(
            """
            <script>
                var width = window.innerWidth;
                var deviceType = 'desktop';
                if (width < 768) {
                    deviceType = 'mobile';
                } else if (width < 992) {
                    deviceType = 'tablet';
                }
                
                // Store in sessionStorage
                sessionStorage.setItem('deviceType', deviceType);
                
                // Reload if device type changed
                var storedType = sessionStorage.getItem('storedDeviceType');
                if (storedType && storedType !== deviceType) {
                    sessionStorage.setItem('storedDeviceType', deviceType);
                    window.location.reload();
                } else {
                    sessionStorage.setItem('storedDeviceType', deviceType);
                }
            </script>
            """,
            unsafe_allow_html=True
        )
    
    return st.session_state.device_type

def responsive_grid(items, columns_desktop=4, columns_tablet=2, columns_mobile=1):
    """
    Create a responsive grid layout.
    
    Args:
        items (list): List of items to display in the grid
        columns_desktop (int): Number of columns on desktop
        columns_tablet (int): Number of columns on tablet
        columns_mobile (int): Number of columns on mobile
        
    Returns:
        list: List of columns with items distributed
    """
    device_type = get_device_type()
    
    if device_type == 'mobile':
        columns = columns_mobile
    elif device_type == 'tablet':
        columns = columns_tablet
    else:
        columns = columns_desktop
    
    # Create columns
    cols = st.columns(columns)
    
    # Distribute items
    for i, item in enumerate(items):
        with cols[i % columns]:
            yield item

def responsive_container(mobile_styles="", tablet_styles="", desktop_styles=""):
    """
    Create a container with responsive styles.
    
    Args:
        mobile_styles (str): CSS styles for mobile
        tablet_styles (str): CSS styles for tablet
        desktop_styles (str): CSS styles for desktop
        
    Returns:
        None
    """
    st.markdown(
        f"""
        <style>
            /* Default (Desktop) */
            .responsive-container {{
                {desktop_styles}
            }}
            
            /* Tablet */
            @media (max-width: 992px) {{
                .responsive-container {{
                    {tablet_styles}
                }}
            }}
            
            /* Mobile */
            @media (max-width: 768px) {{
                .responsive-container {{
                    {mobile_styles}
                }}
            }}
        </style>
        <div class="responsive-container">
        """,
        unsafe_allow_html=True
    )
    
    # Return the closing tag to be used after content
    return "</div>"

def apply_responsive_styles():
    """
    Apply global responsive styles to the application.
    """
    st.markdown(
        """
        <style>
            /* Mobile Optimizations */
            @media (max-width: 768px) {
                /* Make buttons larger and full width */
                .stButton > button {
                    width: 100% !important;
                    height: 3rem !important;
                    font-size: 1rem !important;
                }
                
                /* Adjust input fields */
                div[data-baseweb="input"] > div {
                    height: 3rem !important;
                }
                
                /* Adjust select boxes */
                div[data-baseweb="select"] > div {
                    height: 3rem !important;
                }
                
                /* Adjust text size */
                .stMarkdown p {
                    font-size: 1rem !important;
                }
                
                /* Adjust headers */
                h1 {
                    font-size: 1.8rem !important;
                }
                
                h2 {
                    font-size: 1.5rem !important;
                }
                
                h3 {
                    font-size: 1.2rem !important;
                }
                
                /* Adjust spacing */
                .stVerticalBlock {
                    gap: 1rem !important;
                }
            }
            
            /* Tablet Optimizations */
            @media (min-width: 769px) and (max-width: 992px) {
                /* Adjust button sizes */
                .stButton > button {
                    width: auto !important;
                    height: 2.5rem !important;
                }
                
                /* Adjust headers */
                h1 {
                    font-size: 2rem !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True
    )

def create_responsive_menu(menu_items):
    """
    Create a responsive menu that adapts to different screen sizes.
    
    Args:
        menu_items (list): List of menu items
        
    Returns:
        str: Selected menu item
    """
    device_type = get_device_type()
    
    if device_type == 'mobile':
        # For mobile, use a selectbox
        selected = st.selectbox("Menu", menu_items)
    else:
        # For tablet and desktop, use radio buttons
        selected = st.sidebar.radio("Aller à", menu_items)
    
    return selected

def create_responsive_card(title, content, image=None, key=None):
    """
    Create a responsive card component.
    
    Args:
        title (str): Card title
        content (str): Card content
        image (str, optional): Image path
        key (str, optional): Unique key for the card
        
    Returns:
        None
    """
    device_type = get_device_type()
    
    # Define styles based on device type
    if device_type == 'mobile':
        padding = "0.5rem"
        margin = "0.5rem 0"
        title_size = "1rem"
    elif device_type == 'tablet':
        padding = "0.75rem"
        margin = "0.75rem 0"
        title_size = "1.2rem"
    else:
        padding = "1rem"
        margin = "1rem 0"
        title_size = "1.5rem"
    
    # Create card HTML
    card_html = f"""
    <div style="
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        padding: {padding};
        margin: {margin};
    ">
    """
    
    # Add image if provided
    if image:
        card_html += f'<img src="{image}" style="width: 100%; border-radius: 4px; margin-bottom: 0.5rem;">'
    
    # Add title and content
    card_html += f"""
        <h3 style="font-size: {title_size}; margin-bottom: 0.5rem;">{title}</h3>
        <p style="margin: 0;">{content}</p>
    </div>
    """
    
    # Display card
    st.markdown(card_html, unsafe_allow_html=True)