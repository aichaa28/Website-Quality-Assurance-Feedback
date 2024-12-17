import streamlit as st
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import ssl
import numpy as np
import timeit
import socket
import openai
from dotenv import load_dotenv
import os
from fpdf import FPDF
from datetime import datetime

load_dotenv()


openai.api_key = os.getenv("KEY")  # Use your environment variable for security
def fetch_html_content(url):
    """Fetch HTML content of a web page."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            st.error(f"HTTP Error {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

def analyze_seo(html_content):
    """Analyze SEO elements of a HTML page."""
    soup = BeautifulSoup(html_content, 'html.parser')
    seo_data = {
        "title": soup.title.string if soup.title else "No <title> tag",
        "meta_description": None,
        "alt_missing": [],
        "h1_tags": [],
        "broken_links": []
    }

    # Analyze meta description
    meta_tag = soup.find("meta", attrs={"name": "description"})
    seo_data["meta_description"] = meta_tag["content"] if meta_tag else "No meta description tag"

    # Analyze images without ALT attribute
    images = soup.find_all("img")
    for img in images:
        if not img.get("alt"):
            seo_data["alt_missing"].append(img.get("src"))

    # Analyze H1 tags
    h1_tags = soup.find_all("h1")
    seo_data["h1_tags"] = [h1.text.strip() for h1 in h1_tags]

    # Check for broken links
    links = soup.find_all("a", href=True)
    for link in links:
        href = link["href"]
        if href.startswith("http"):
            try:
                link_response = requests.head(href, timeout=3)
                if link_response.status_code >= 400:
                    seo_data["broken_links"].append(href)
            except:
                seo_data["broken_links"].append(href)

    return seo_data

def generate_llm_feedback(seo_results):
    """Generate an SEO report using an LLM (GPT-4)."""
    prompt = f"""
    Here are the SEO analysis results for a web page:

    - Title: {seo_results['title']}
    - Meta Description: {seo_results['meta_description']}
    - Images without ALT: {len(seo_results['alt_missing'])} images
    - H1 Tags: {seo_results['h1_tags']}
    - Broken Links: {len(seo_results['broken_links'])} links

    Provide a detailed analysis identifying SEO weaknesses and suggest recommendations for improvement.
    """

    try:
        response = openai.ChatCompletion.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "You are an expert in SEO and web optimization."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )

        if response and 'choices' in response:
            return response['choices'][0]['message']['content']
        else:
            return "Error generating the LLM report."
    except Exception as e:
        return f"OpenAI API Error: {e}"

def generate_report(report_content):
    """Function to generate a report using the OpenAI API"""
    report_input = f"""
    Analyzing website feedback report:

    Performance: {report_content['Performance']}
    Usability: {report_content['Usability']}
    Accessibility: {report_content['Accessibility']}
    Security: {report_content['Security']}
    Compatibility: {report_content['Compatibility']}
    HTML Validity: {report_content['HTML Validity']}

    Provide a detailed analysis in a single continuous paragraph, covering all aspects comprehensively. 
    Include metrics such as response time, load time, usability issues, accessibility concerns (like missing alt text for images), security problems, and compatibility across different devices and browsers. 
    Offer actionable suggestions for improvements.
    """

    try:
        response = openai.ChatCompletion.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "You are an expert in website analysis."},
                {"role": "user", "content": report_input}
            ],
            max_tokens=1000,  # Adjust the token limit
            temperature=0.7
        )

        if response and 'choices' in response and response['choices']:
            generated_text = response['choices'][0]['message']['content'].strip()
            return generated_text
        else:
            print("Unexpected response structure.")
            return None

    except Exception as e:
        print(f"Error communicating with OpenAI: {e}")
        return None

def check_performance(url, num_samples=10): # Function to check performance
    load_times = []  # Store load times
    response_times = []  # Store response times
    
    # Measure the performance 'num_samples' times
    for _ in range(num_samples):
        start = timeit.default_timer()  # Start time
        response = requests.get(url)  # Perform GET request
        end = timeit.default_timer()  # End time
        load_times.append(end - start)  # Total time for request
        response_times.append(response.elapsed.total_seconds())  # Time from server

    # Calculate averages
    avg_load_time = sum(load_times) / num_samples
    avg_response_time = sum(response_times) / num_samples
    
    # Return the performance metrics
    return {
        'avg_load_time': avg_load_time,
        'avg_response_time': avg_response_time,
        'load_times': load_times,
        'response_times': response_times
    }


def plot_performance(performance_feedback):
    # Create the figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
    
    # Plot load times
    ax1.hist(performance_feedback['load_times'], bins=10, color='skyblue', edgecolor='black')
    ax1.set_title('Distribution of Load Times')
    ax1.set_xlabel('Load Time (s)')
    ax1.set_ylabel('Number of Samples')
    ax1.grid(True, linestyle='--', alpha=0.7)
    st.write("**Explanation for Load Times Plot**:")
    st.write("The histogram displays the distribution of load times in seconds across the samples. It shows how quickly the website loads for different sample requests. ")
    # Plot response times
    ax2.hist(performance_feedback['response_times'], bins=10, color='coral', edgecolor='black')
    ax2.set_title('Distribution of Response Times')
    ax2.set_xlabel('Response Time (s)')
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    return fig


def check_usability(url): # Function to check usability based on navigation, content clarity, aesthetics, readability, and style consistency.
    feedback = {
        'navigation': {'score': 0, 'description': ''},
        'content_clarity': {'score': 0, 'description': ''},
        'aesthetic': {'score': 0, 'description': ''},
        'readability': {'score': 0, 'description': ''},
        'style_consistency': {'score': 0, 'description': ''},
    }

    # Check if the site is accessible
    try:
        response = requests.get(url, timeout=5)  # Timeout of 5 seconds
        status_code = response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Error checking the site: {e}")
        return feedback  # Return feedback on error

    if status_code != 200:
        feedback['navigation']['description'] = 'The site is not accessible, status code: {}'.format(status_code)
        return feedback

    soup = BeautifulSoup(response.text, 'html.parser')

    # 1. Evaluate navigation (check for broken links)
    links = soup.find_all('a')
    total_links = len(links)
    broken_links = [link for link in links if link.get('href') and 'http' not in link['href']]
    broken_links_count = len(broken_links)
    navigation_score = (1 - broken_links_count / total_links) * 100 if total_links else 0
    feedback['navigation']['score'] = navigation_score
    feedback['navigation']['description'] = f'{broken_links_count}/{total_links} links are broken'

    # 2. Evaluate content clarity (empty paragraphs)
    paragraphs = soup.find_all('p')
    total_paragraphs = len(paragraphs)
    empty_paragraphs = [p for p in paragraphs if not p.text.strip()]
    empty_paragraphs_count = len(empty_paragraphs)
    content_clarity_score = (1 - empty_paragraphs_count / total_paragraphs) * 100 if total_paragraphs else 0
    feedback['content_clarity']['score'] = content_clarity_score
    feedback['content_clarity']['description'] = f'{empty_paragraphs_count}/{total_paragraphs} paragraphs are empty'

    # 3. Evaluate aesthetics (missing images)
    images = soup.find_all('img')
    total_images = len(images)
    missing_images = [img for img in images if 'src' not in img.attrs or not img['src']]
    missing_images_count = len(missing_images)
    aesthetic_score = (1 - missing_images_count / total_images) * 100 if total_images else 0
    feedback['aesthetic']['score'] = aesthetic_score
    feedback['aesthetic']['description'] = f'{missing_images_count}/{total_images} images are missing'

    # 4. Evaluate readability (text length)
    texts = soup.find_all(['p', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    readable_texts = [t for t in texts if len(t.text.strip()) > 50]  # Minimum threshold for text length
    readability_score = len(readable_texts) / len(texts) * 100 if texts else 0
    feedback['readability']['score'] = readability_score
    feedback['readability']['description'] = f'{len(readable_texts)}/{len(texts)} texts meet readability standards'

    # 5. Check for consistent styling (CSS presence)
    css_links = soup.find_all('link', {'rel': 'stylesheet'})
    inline_styles = soup.find_all(style=True)
    if css_links or inline_styles:
        feedback['style_consistency']['score'] = 100
        feedback['style_consistency']['description'] = 'The website has consistent styling with CSS.'
    else:
        feedback['style_consistency']['score'] = 0
        feedback['style_consistency']['description'] = 'No consistent styling detected (missing CSS).'

    return feedback


def check_accessibility(url):  # Function to check the accessibility
    feedback = {
        'compliant': 0,
        'non_compliant': 0,
        'details': {}
    }
    try:
        # Fetch page content
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception if the request fails
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Check for images with 'alt' attributes ---
        images = soup.find_all('img')
        compliant_images = sum(1 for img in images if img.get('alt'))  # Images with 'alt'
        non_compliant_images = len(images) - compliant_images

        # --- Check for empty headings ---
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        empty_headings = sum(1 for h in headings if not h.text.strip())  # Headings without visible text

        # --- Check for the 'lang' attribute in <html> ---
        html_tag = soup.find('html')
        lang_attribute = html_tag.get('lang') if html_tag else None
        lang_compliant = bool(lang_attribute)

        # --- Weighting and scoring ---
        total_checks = len(images) + len(headings) + 1  # Adding 1 for the 'lang' check
        total_compliant = compliant_images + (len(headings) - empty_headings) + int(lang_compliant)

        if total_checks > 0:
            feedback['compliant'] = int((total_compliant / total_checks) * 100)
            feedback['non_compliant'] = 100 - feedback['compliant']
        else:
            feedback['compliant'] = 100  # Empty page is considered fully compliant

        # --- Details of checks ---
        feedback['details'] = {
            'total_images': len(images),
            'images_with_alt': compliant_images,
            'images_without_alt': non_compliant_images,
            'total_headings': len(headings),
            'empty_headings': empty_headings,
            'html_lang_present': lang_compliant
        }

    except requests.exceptions.RequestException as e:
        return {'error': f"Failed to retrieve page content: {str(e)}"}

    return feedback


def plot_accessibility(feedback):
    # Extract values
    compliant = feedback.get('compliant', 0)
    non_compliant = feedback.get('non_compliant', 0)
    
    # Validation of values
    if compliant < 0 or non_compliant < 0:
        raise ValueError("Values for 'compliant' and 'non_compliant' must be non-negative.")
    
    if compliant + non_compliant == 0:
        raise ValueError("Values 'compliant' and 'non-compliant' cannot both be zero.")
    
    # Filter out 0% values to avoid empty chart sections
    labels = []
    sizes = []
    colors = []
    
    if compliant > 0:
        labels.append('Compliant')
        sizes.append(compliant)
        colors.append('#4CAF50')  # Green color for compliant
    
    if non_compliant > 0:
        labels.append('Non-Compliant')
        sizes.append(non_compliant)
        colors.append('#F44336')  # Red color for non-compliant
    
    # Plot the pie chart
    fig, ax = plt.subplots(figsize=(6, 6))  # Ensures a clean, square figure
    ax.pie(
        sizes,
        labels=labels,
        autopct='%1.1f%%',
        colors=colors,
        startangle=90,  # Start the chart from the top
        wedgeprops={'edgecolor': 'white'}  # Clean separation between segments
    )
    ax.set_title('Accessibility Compliance Feedback', fontsize=14, fontweight='bold')
    ax.axis('equal')  # Ensures the pie chart is circular
    
    # Return the plot object
    return plt


def check_security(url):
    feedback = {'secure': 0, 'insecure': 0}
    details = []  # To store details of each step
    total_checks = 6  # Updated total checks
    contribution_per_check = 100 / total_checks

    # Step 1: Check if HTTPS is used
    if url.startswith("https://"):
        feedback['secure'] += contribution_per_check
        details.append(f"✔️ Step 1: HTTPS is used. (+{contribution_per_check:.2f}%)")
    else:
        feedback['insecure'] += contribution_per_check
        details.append(f"❌ Step 1: HTTPS is not used. (+0%)")

    # Step 2: Verify SSL certificate validity
    try:
        context = ssl.create_default_context()
        with context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=url) as connection:
            connection.settimeout(5)
            connection.connect((url, 443))
            certificate = connection.getpeercert()
            if certificate:
                expiry_date = datetime.strptime(certificate['notAfter'], '%b %d %H:%M:%S %Y %Z')
                if expiry_date > datetime.now():
                    feedback['secure'] += contribution_per_check
                    details.append(f"✔️ Step 2: SSL certificate is valid and not expired. (+{contribution_per_check:.2f}%)")
                else:
                    feedback['insecure'] += contribution_per_check
                    details.append("❌ Step 2: SSL certificate has expired. (+0%)")
            else:
                feedback['insecure'] += contribution_per_check
                details.append("❌ Step 2: No SSL certificate found. (+0%)")
    except:
        feedback['insecure'] += contribution_per_check
        details.append("❌ Step 2: Unable to verify SSL certificate. (+0%)")

    # Step 3: Verify if the URL is accessible without errors
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            feedback['secure'] += contribution_per_check
            details.append(f"✔️ Step 3: URL is accessible without errors. (+{contribution_per_check:.2f}%)")
        else:
            feedback['insecure'] += contribution_per_check
            details.append(f"❌ Step 3: URL returned status code {response.status_code}. (+0%)")
    except:
        feedback['insecure'] += contribution_per_check
        details.append("❌ Step 3: URL is not accessible. (+0%)")

    # Step 4: Check for HTTP security headers
    try:
        response = requests.get(url, timeout=5)
        headers = response.headers
        required_headers = ['Strict-Transport-Security', 'Content-Security-Policy', 'X-Frame-Options', 'X-Content-Type-Options']
        missing_headers = [header for header in required_headers if header not in headers]
        if not missing_headers:
            feedback['secure'] += contribution_per_check
            details.append(f"✔️ Step 4: All required HTTP security headers are present. (+{contribution_per_check:.2f}%)")
        else:
            feedback['insecure'] += contribution_per_check
            details.append(f"❌ Step 4: Missing HTTP security headers: {', '.join(missing_headers)}. (+0%)")
    except:
        feedback['insecure'] += contribution_per_check
        details.append("❌ Step 4: Unable to check HTTP security headers. (+0%)")

    # Step 5: Check for XSS protection
    try:
        response = requests.get(url, timeout=5)
        headers = response.headers
        if 'X-XSS-Protection' in headers and headers['X-XSS-Protection'] == '1; mode=block':
            feedback['secure'] += contribution_per_check
            details.append(f"✔️ Step 5: X-XSS-Protection header is correctly configured. (+{contribution_per_check:.2f}%)")
        else:
            feedback['insecure'] += contribution_per_check
            details.append("❌ Step 5: X-XSS-Protection header is missing or misconfigured. (+0%)")
    except:
        feedback['insecure'] += contribution_per_check
        details.append("❌ Step 5: Unable to verify X-XSS-Protection header. (+0%)")

    # Step 6: Check for Open Ports
    try:
        hostname = url.replace("https://", "").replace("http://", "").split('/')[0]
        open_ports = []
        for port in [21, 22, 23, 25, 110, 143]:  # Common vulnerable ports
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                if sock.connect_ex((hostname, port)) == 0:
                    open_ports.append(port)
        if not open_ports:
            feedback['secure'] += contribution_per_check
            details.append(f"✔️ Step 6: No common vulnerable ports are open. (+{contribution_per_check:.2f}%)")
        else:
            feedback['insecure'] += contribution_per_check
            details.append(f"❌ Step 6: Open vulnerable ports found: {', '.join(map(str, open_ports))}. (+0%)")
    except:
        feedback['insecure'] += contribution_per_check
        details.append("❌ Step 6: Unable to check for open ports. (+0%)")

    # Calculate insecure percentage
    feedback['insecure'] = 100 - feedback['secure']
    return feedback, details


def check_compatibility(url):
    try:
        # Tester sur l'ordinateur
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
            compatible_computer = bool(viewport_meta)

            # Vérification de la mise en page sur l'ordinateur
            container = soup.find('div', class_='container') or soup.find('main') or soup.find('body')
            if container:
                style = container.get('style', '')
                if 'max-width' in style and 'px' in style:
                    max_width = int(style.split('max-width')[1].strip().split('px')[0])
                    if max_width >= 1200:
                        compatible_computer = False
                        message = "Le site n'est pas compatible sur l'ordinateur. La mise en page ne s'adapte pas bien aux écrans larges."
                    else:
                        message = "Le site est compatible sur l'ordinateur."

        else:
            compatible_computer = False
            message = f"Le site n'est pas accessible sur l'ordinateur. Code de statut HTTP : {response.status_code}"

        # Tester sur un appareil mobile
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'
        }
        mobile_response = requests.get(url, headers=headers)
        if mobile_response.status_code == 200:
            mobile_soup = BeautifulSoup(mobile_response.content, 'html.parser')
            viewport_meta_mobile = mobile_soup.find('meta', attrs={'name': 'viewport'})
            compatible_mobile = bool(viewport_meta_mobile)

            # Vérification de la mise en page sur mobile
            mobile_container = mobile_soup.find('div', class_='container') or mobile_soup.find('main') or mobile_soup.find('body')
            if mobile_container:
                style = mobile_container.get('style', '')
                if 'max-width' in style and 'px' in style:
                    max_width = int(style.split('max-width')[1].strip().split('px')[0])
                    if max_width > 480:
                        compatible_mobile = False
                        message = "Le site n'est pas compatible sur le mobile. La mise en page ne s'adapte pas correctement aux petits écrans."
                    else:
                        message = "Le site est compatible sur le mobile."

        else:
            compatible_mobile = False
            message = f"Le site n'est pas accessible sur le mobile. Code de statut HTTP : {mobile_response.status_code}"

        # Retour de la compatibilité
        if compatible_computer and compatible_mobile:
            return "Le site est compatible à la fois sur l'ordinateur et sur le mobile."
        elif compatible_computer:
            return "Le site est compatible sur l'ordinateur mais pourrait avoir des problèmes sur le mobile."
        elif compatible_mobile:
            return "Le site est compatible sur le mobile mais pourrait avoir des problèmes sur l'ordinateur."
        else:
            return "Le site n'est pas compatible ni sur l'ordinateur ni sur le mobile."
    except Exception as e:
        return f"Erreur lors de la vérification de compatibilité : {str(e)}"


def check_html_validity(url):
    feedback = {"valid": True, "errors": []}
    try:
        # Make an HTTP request
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Check if there are improperly closed tags
        errors = soup.find_all(lambda tag: tag.parent.name == "pre" and len(tag.find_all()) > 0)
        if errors:
            feedback["valid"] = False
            feedback["errors"] = [str(error) for error in errors]
    except Exception as e:
        feedback["valid"] = False
        feedback["errors"].append(f"Error during HTML validation: {e}")
    
    return feedback


def generate_pdf(report):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, report)
    return pdf

# Streamlit App
st.title('Website Quality Assurance Feedback')
url = st.text_input('Enter the URL of the website:')

if url:
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8= st.tabs(["Performance", "Usability", "Accessibility", "Security", "Compatibility","HTML Validity","Report","SEO Report"])

    with tab1:
        st.header("📊 Web performance")
        performance_feedback = check_performance(url, 20)
        st.write(f"**Average Load Time:** {performance_feedback['avg_load_time']:.2f} seconds")
        st.write(f"**Average Response Time:** {performance_feedback['avg_response_time']:.2f} seconds")
        with st.expander("View Performance Distributions"):
            st.pyplot(plot_performance(performance_feedback))
    with tab2:
        st.header("🖥️ Web Usability Feedback")

        # Perform usability check
        usability_feedback = check_usability(url)
        
        # Check for errors in usability feedback
        if 'error' in usability_feedback:
            st.error(f"❌ Failed to perform usability analysis. Error: {usability_feedback['error']}")
        
        # Introduction to usability analysis
        st.markdown("""
        **Usability Analysis evaluates how user-friendly and efficient a website is.**
        The following criteria have been assessed:
        - **Navigation**: Ease of navigating the website.
        - **Content Clarity**: How clear and understandable the content is.
        - **Aesthetic**: Visual appeal of the website.
        - **Readability**: How readable the text is for users.
        - **Style Consistency**: Uniformity of the design and content style.
        """)
        
        st.subheader("🔍 Usability Scores and Details")
        
        # Layout using columns for better presentation
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("### 🧭 Navigation")
            st.write(f"**Score:** {usability_feedback['navigation']['score']:.2f}%")
            st.write(f"**Details:** {usability_feedback['navigation']['description']}")
            
            st.info("### ✏️ Content Clarity")
            st.write(f"**Score:** {usability_feedback['content_clarity']['score']:.2f}%")
            st.write(f"**Details:** {usability_feedback['content_clarity']['description']}")
        
        with col2:
            st.info("### 🎨 Aesthetic")
            st.write(f"**Score:** {usability_feedback['aesthetic']['score']:.2f}%")
            st.write(f"**Details:** {usability_feedback['aesthetic']['description']}")
            
            st.info("### 📖 Readability")
            st.write(f"**Score:** {usability_feedback['readability']['score']:.2f}%")
            st.write(f"**Details:** {usability_feedback['readability']['description']}")
        
        # Style Consistency as a single row below columns
        st.subheader("🎯 Style Consistency")
        st.success(f"**Score:** {usability_feedback['style_consistency']['score']}%")
        st.write(f"**Details:** {usability_feedback['style_consistency']['description']}")

    with tab3:
        st.header("🌐 Web Accessibility Feedback")
        
        # Fetch accessibility feedback
        accessibility_feedback = check_accessibility(url)
        
        # Error handling for failed URL fetch
        if 'error' in accessibility_feedback:
            st.error(f"❌ Failed to fetch the webpage. Error: {accessibility_feedback['error']}")
        
        # Explanation of compliance and verification checks
        st.markdown("""
        **In the context of web accessibility:**
        - **Compliant** refers to elements of the website that adhere to accessibility standards.
        - **Non-Compliant** indicates elements that do not meet these standards.
        """)
        
        st.subheader("✅ Accessibility Checks Performed")
        st.markdown("""
        The following verifications were conducted to assess the website's accessibility:
        - **Images:** Presence of the `alt` attribute for all `<img>` tags.
        - **Headings:** Ensuring headings (`<h1>`, `<h2>`, etc.) are not empty.
        - **General Elements:** Counting the total number of images and headings.
        
        The compliance percentage is calculated based on these checks.
        """)

        # Display feedback results
        compliant = accessibility_feedback['compliant']
        non_compliant = accessibility_feedback['non_compliant']
        
        col1, col2 = st.columns(2)  # Layout with two columns
        
        with col1:
            st.info(f"✅ **Compliant:** {compliant}%")
        
        with col2:
            st.warning(f"⚠️ **Non-Compliant:** {non_compliant}%")
        
        # Display pie chart
        st.subheader("📊 Accessibility Compliance Chart")
        try:
            plot = plot_accessibility(accessibility_feedback)
            st.pyplot(plot)
        except ValueError as e:
            st.error(f"❌ Error generating the chart: {str(e)}")

    with tab4:
        st.header("🔒 Web Security Feedback")
        result, details = check_security(url)

        # Display results
        st.subheader("Security Check Results")
        st.write(f"**Secure:** {result['secure']:.2f}%")
        st.write(f"**Insecure:** {result['insecure']:.2f}%")

        # Progress bar for secure score
        st.progress(result['secure'] / 100)

        # Display step-by-step details
        st.subheader("Step-by-Step Details")
        for detail in details:
            st.write(detail)

        # Provide insights based on the results
        st.subheader("Insights:")
        if result['secure'] == 100:
            st.success("This website is highly secure!")
        elif result['secure'] >= 70:
            st.info("This website has good security, but some improvements are recommended.")
        else:
            st.warning("This website has significant security risks.")
    with tab5:
        st.subheader("🛠️ Compatibility Check")
        compatibility_feedback = check_compatibility(url)
        st.write(compatibility_feedback)
    with tab6:
        feedback_html = check_html_validity(url)

        # Display results
        st.subheader("🖥️ HTML Validation Results")
        if feedback_html["valid"]:
            st.success("The HTML structure of the website is valid!")
        else:
            st.error("The website has HTML errors!")

            # Display errors if any
            if feedback_html["errors"]:
                st.subheader("Details of Errors")
                for error in feedback_html["errors"]:
                    st.code(error, language="html")
    with tab7 :
        st.header("📄 Generated Report")
        report_content = {
            'Performance': performance_feedback,
            'Usability': usability_feedback,
            'Accessibility': accessibility_feedback,
            'Security': detail,
            'Compatibility': compatibility_feedback,
            'HTML Validity': feedback_html
        }
        report = generate_report(report_content)
        st.text(report)

        if st.button("Download the report in PDF"):
            pdf = generate_pdf(report)
            pdf_output = "rapport.pdf"
            pdf.output(pdf_output)
            with open(pdf_output, "rb") as file:
                st.download_button(
                    label="Click here to download",
                    data=file,
                    file_name=pdf_output,
                    mime="application/pdf"
                )
        with tab8:
            html_content = fetch_html_content(url)
            seo_results = analyze_seo(html_content)
            st.subheader("SEO Report")
            report = generate_llm_feedback(seo_results)
            st.write(report)