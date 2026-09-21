# Omnix AI — Current Status & Upgrade Report
*Generated: September 21, 2026*

## 1. What We Are Currently Doing
We are currently in a **stabilization phase** at the end of **Phase 8** (System Intel & OS Controls). Instead of rushing blindly into Phase 9 (Email Automation & Macros), we are hardening the core foundation of Omnix. The primary focus right now is ensuring that Omnix can reliably see the screen, interact with UI elements, and manage files without guessing or crashing.

## 2. What We Are Upgrading Currently
*   **The Vision Engine (Cloud Vision Upgrade):** We are migrating the primary visual interaction system from a "blind" local OCR (`EasyOCR`) to a **Cloud LLM Vision system (Gemini)**. Instead of just reading text, Omnix can now send a screenshot to Gemini to get exact X,Y coordinates for complex UI elements, icons (like a "gear icon"), and buttons (like WhatsApp's "Open app" prompt).
*   **Settings UI:** Added a toggle in the UI so the user can freely switch between Cloud Vision (Gemini) and Local Vision (EasyOCR/CPU).
*   **System Audio Controls:** Completely gutted the unreliable `pycaw` Python library (which crashed on certain Windows audio drivers) and replaced it with a dependency-free, native PowerShell C# script for bulletproof volume control.
*   **Agent Behavioral Logic ("Look Before You Leap"):** Upgrading Omnix's prompt logic so it no longer hallucinates file paths. It is now strictly instructed to use `list_directory` to physically check a folder before trying to copy, move, or read a file.

## 3. What is Lacking Behind Currently
*   **Speed vs. Precision Trade-off:** By moving to Cloud Vision (Gemini) for clicking UI elements, we gain massive precision, but we sacrifice a bit of speed because the image has to be uploaded to the cloud and processed. 
*   **100% Offline Capability:** The Local Vision (EasyOCR) system is struggling to be precise enough for a fully autonomous agent without a dedicated NVIDIA GPU. Relying on Cloud Vision means Omnix needs an internet connection to "see" properly.
*   **Context Window Limits:** As we add more skills (currently over 50), the system prompt is getting very large. We need to ensure the AI doesn't get "distracted" by having too many tools available at once.

## 4. Problem Classification & Current Fixes

### 🔴 Major Problems (Critical Blockers)
1.  **Vision Precision (UI Targeting):**
    *   *Issue:* Omnix was clicking random WhatsApp chats or failing to find the "Open app" button because local OCR only matches text strings and struggles with contrast/scaling.
    *   *Current Fix:* Implemented `click_visual` skill utilizing Gemini's multimodal capabilities to return exact X,Y coordinates.
2.  **File Path Hallucination:**
    *   *Issue:* When asked to copy "text" on the desktop, Omnix would blindly guess the path was `C:\Users\chira\Desktop\text.tst`, failing repeatedly and wasting time.
    *   *Current Fix:* Enforced **Rule 32** in the AI's brain, forcing it to use `list_directory` first.

### 🟡 Medium Problems (Reliability & Dependencies)
1.  **Hardware/Driver Incompatibilities:**
    *   *Issue:* `set_volume` was crashing with a COM (`AudioDevice`) error due to `pycaw` clashing with the local audio driver setup.
    *   *Current Fix:* Bypassed Python libraries entirely for volume control, injecting native C# into PowerShell.
2.  **Deep-link Navigation Stalling:**
    *   *Issue:* `open_url("https://wa.me/...")` successfully opened the browser, but the agent stalled out because it couldn't figure out how to click the final confirmation prompt.
    *   *Current Fix:* The new Cloud Vision system will bridge this gap, allowing the AI to naturally "see" the prompt and click it.

### 🟢 Basic Problems (Minor Polish)
1.  **Pin Memory / CUDA Warnings:**
    *   *Issue:* EasyOCR throws `pin_memory` warnings when forced to run on CPU. 
    *   *Current Fix:* Ignored warnings safely; added UI warnings to let the user know CPU processing is slow.
2.  **Notification Fallbacks:**
    *   *Issue:* `win10toast` sometimes hangs if the Windows Notification Center is suppressed.
    *   *Current Fix:* Added a PowerShell BalloonTip fallback in `show_notification` to ensure alerts always display.

## 5. Next Steps
Once the user (Chirag) tests the **Cloud Vision** and **Volume/File Ops** fixes and confirms they are 100% stable, Omnix will be ready to begin **Phase 9**. Phase 9 will introduce:
*   Email reading/sending capabilities.
*   Custom macro recording (automating repetitive clicks/typing).
*   Scheduled background tasks.
