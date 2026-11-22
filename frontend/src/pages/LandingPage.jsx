import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Navbar from "../components/shared/Navbar";
import Footer from "../components/shared/Footer";
import "./LandingPage.css";

// Reliable, high-quality, authentic food donation & community sharing photographs
const PRIMARY_HERO_IMAGE =
  "https://images.unsplash.com/photo-1593113598332-cd288d649433?auto=format&fit=crop&w=1200&q=80";
const FALLBACK_HERO_IMAGE =
  "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=1200&q=80";

function LandingPage() {
  const { user } = useAuth();
  const [heroImgSrc, setHeroImgSrc] = useState(PRIMARY_HERO_IMAGE);

  const handleImageError = () => {
    if (heroImgSrc !== FALLBACK_HERO_IMAGE) {
      setHeroImgSrc(FALLBACK_HERO_IMAGE);
    }
  };

  return (
    <div className="landing-page-wrapper">
      <Navbar />

      <main>
        {/* =================================================================
            HERO SECTION
            ================================================================= */}
        <section className="hero-section">
          <div className="hero-container">
            <div className="hero-content">
              <div className="hero-badge">
                <span className="hero-badge-dot"></span>
                <span>Community Food Network</span>
              </div>

              <h1 className="hero-title">
                Turn Surplus Food Into <span className="hero-highlight">Community Nourishment.</span>
              </h1>

              <p className="hero-description">
                ShareMeal connects restaurants, caterers, grocery stores, and compassionate individuals with verified community receivers. Fresh, safe surplus food belongs on tables, not in landfills.
              </p>

              {/* Prominent Redesigned CTA Buttons */}
              <div className="hero-cta-group">
                <Link
                  to={user ? "/donor" : "/login"}
                  className="hero-btn-primary"
                >
                  Donate Surplus Food
                </Link>
                <Link
                  to={user ? "/receiver" : "/login"}
                  className="hero-btn-secondary"
                >
                  Find Community Food
                </Link>
              </div>

              <div className="hero-trust-indicators">
                <div className="trust-item">
                  <svg className="trust-icon" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                  </svg>
                  <span>100% Free Food Exchange</span>
                </div>
                <div className="trust-item">
                  <svg className="trust-icon" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                  </svg>
                  <span>Verified Receiver Vetting</span>
                </div>
                <div className="trust-item">
                  <svg className="trust-icon" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                  </svg>
                  <span>Strict Hygiene Checklists</span>
                </div>
              </div>
            </div>

            {/* High-quality realistic food photograph */}
            <div className="hero-visual">
              <div className="hero-image-card">
                <img
                  src={heroImgSrc}
                  onError={handleImageError}
                  alt="Fresh meals and wholesome produce packaged for community food sharing"
                  className="hero-main-img"
                />
                <div className="hero-floating-card top-right">
                  <div className="floating-card-icon">🍲</div>
                  <div>
                    <div className="floating-card-title">Fresh Meals</div>
                    <div className="floating-card-sub">Prepared with care</div>
                  </div>
                </div>
                <div className="hero-floating-card bottom-left">
                  <div className="floating-card-icon">🌱</div>
                  <div>
                    <div className="floating-card-title">Zero Waste Mission</div>
                    <div className="floating-card-sub">Local food sovereignty</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* =================================================================
            HOW IT WORKS SECTION
            ================================================================= */}
        <section id="how-it-works" className="how-it-works-section">
          <div className="section-container">
            <div className="section-header">
              <span className="section-eyebrow">Simplicity &amp; Transparency</span>
              <h2 className="section-title">How ShareMeal Works</h2>
              <p className="section-subtitle">
                A seamless, respectful bridge designed for speed, safety, and community dignity.
              </p>
            </div>

            <div className="steps-grid">
              <div className="step-card">
                <div className="step-number">01</div>
                <div className="step-icon-wrapper">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 20h9M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <h3 className="step-title">Donors Post Surplus</h3>
                <p className="step-text">
                  Donors list available meals with quantity, human or animal category, safe-until window, and complete a 4-point hygiene safety verification.
                </p>
              </div>

              <div className="step-card">
                <div className="step-number">02</div>
                <div className="step-icon-wrapper">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="M21 21l-4.35-4.35M11 8v6M8 11h6" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <h3 className="step-title">Verified Receivers Browse</h3>
                <p className="step-text">
                  Local shelters, community kitchens, and verified individuals search food within safe radius distance and claim needed listings.
                </p>
              </div>

              <div className="step-card">
                <div className="step-number">03</div>
                <div className="step-icon-wrapper">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" strokeLinecap="round" strokeLinejoin="round"/>
                    <circle cx="12" cy="10" r="3"/>
                  </svg>
                </div>
                <h3 className="step-title">Safe &amp; Timely Handover</h3>
                <p className="step-text">
                  Upon verified claim, exact pickup addresses and GPS navigation unlock. Meals are collected safely before the freshness deadline.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* =================================================================
            SAFETY & TRUST SECTION
            ================================================================= */}
        <section className="safety-section">
          <div className="section-container">
            <div className="safety-grid">
              <div className="safety-content">
                <span className="section-eyebrow">Integrity &amp; Care</span>
                <h2 className="section-title">Built with uncompromising food safety standards.</h2>
                <p className="safety-lead">
                  Every food interaction on ShareMeal is anchored in transparent food handling protocols so that food reaches receivers at peak safety and freshness.
                </p>

                <div className="safety-features-list">
                  <div className="safety-feature-item">
                    <div className="feature-bullet">✓</div>
                    <div>
                      <h4 className="feature-title">Mandatory 4-Point Hygiene Protocols</h4>
                      <p className="feature-desc">Sanitary preparation spaces, clean transit containers, and proper post-cooking temperature control.</p>
                    </div>
                  </div>

                  <div className="safety-feature-item">
                    <div className="feature-bullet">✓</div>
                    <div>
                      <h4 className="feature-title">Enforced Safe-Until Freshness Clocks</h4>
                      <p className="feature-desc">Every donation specifies a non-negotiable safe-until window. Expired food automatically de-lists.</p>
                    </div>
                  </div>

                  <div className="safety-feature-item">
                    <div className="feature-bullet">✓</div>
                    <div>
                      <h4 className="feature-title">Donor Privacy &amp; Secure Unlocking</h4>
                      <p className="feature-desc">Exact pickup addresses are kept confidential until an authorized, verified receiver officially claims the batch.</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="safety-card-container">
                <div className="safety-highlight-card">
                  <h3 className="highlight-card-title">Hygiene Commitment</h3>
                  <ul className="highlight-list">
                    <li>
                      <span className="check-mark">✔</span> Clean utensils and sanitary surfaces during prep
                    </li>
                    <li>
                      <span className="check-mark">✔</span> Food kept at regulated holding temperatures
                    </li>
                    <li>
                      <span className="check-mark">✔</span> Covered, spill-proof packaging for secure transit
                    </li>
                    <li>
                      <span className="check-mark">✔</span> Clear segregation of human and animal food streams
                    </li>
                  </ul>
                  <div className="highlight-footer">
                    <span>Admin reviewed receiver credentials</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* =================================================================
            COMMUNITY IMPACT SECTION (NON-NUMERICAL)
            ================================================================= */}
        <section id="impact" className="impact-section">
          <div className="section-container">
            <div className="section-header">
              <span className="section-eyebrow">Our Social &amp; Ecological Mission</span>
              <h2 className="section-title">Why ShareMeal Exists</h2>
              <p className="section-subtitle">
                Food is a fundamental human right. Waste is a preventable tragedy.
              </p>
            </div>

            <div className="impact-cards-grid">
              <div className="impact-card">
                <div className="impact-card-icon">🌍</div>
                <h3 className="impact-card-title">Landfill Waste Diversion</h3>
                <p className="impact-card-desc">
                  Edible food discarded in landfills decomposes into potent greenhouse gases. By redirecting surplus meals directly to tables, we preserve agricultural resources and safeguard our shared climate.
                </p>
              </div>

              <div className="impact-card">
                <div className="impact-card-icon">🤝</div>
                <h3 className="impact-card-title">Direct Neighborhood Solidarity</h3>
                <p className="impact-card-desc">
                  Instead of lengthy bureaucratic charity pipelines, ShareMeal facilitates hyper-local peer-to-peer distribution, fostering mutual aid, dignity, and strong communal bonds.
                </p>
              </div>

              <div className="impact-card">
                <div className="impact-card-icon">🐾</div>
                <h3 className="impact-card-title">Responsible Dual Streams</h3>
                <p className="impact-card-desc">
                  Not all surplus is suitable for human tables. ShareMeal explicitly supports animal feed donations, empowering local shelters, sanctuaries, and farms to nourish animals sustainably.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* =================================================================
            CALL TO ACTION BANNER
            ================================================================= */}
        <section className="cta-banner-section">
          <div className="section-container">
            <div className="cta-banner-card">
              <h2 className="cta-banner-title">Make a tangible difference in your community today.</h2>
              <p className="cta-banner-subtitle">
                Whether you have five extra meal boxes from an event or a community kitchen looking to receive fresh produce, your involvement matters.
              </p>
              <div className="cta-banner-buttons">
                <Link
                  to={user ? "/donor" : "/login"}
                  className="hero-btn-primary"
                >
                  Donate Surplus Food
                </Link>
                <Link
                  to={user ? "/receiver" : "/login"}
                  className="hero-btn-secondary cta-btn-secondary"
                >
                  Find Community Food
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}

export default LandingPage;
