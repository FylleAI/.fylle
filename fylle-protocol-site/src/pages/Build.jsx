import { Link } from 'react-router-dom'
import { useEffect } from 'react'

export default function Build() {
  useEffect(() => {
    const reveals = document.querySelectorAll('.reveal')
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          setTimeout(() => {
            entry.target.classList.add('visible')
          }, i * 80)
          observer.unobserve(entry.target)
        }
      })
    }, { threshold: 0.15 })
    reveals.forEach(el => observer.observe(el))
    return () => observer.disconnect()
  }, [])

  return (
    <div className="landing-page">
      {/* Nav */}
      <nav className="build-nav">
        <div className="build-logo">fylle<span>.</span>build</div>
        <div className="build-nav-tag">Internal — Feb 2025</div>
      </nav>

      {/* Hero */}
      <section className="build-hero">
        <div className="build-hero-glow"></div>
        <div className="build-container">
          <div className="build-hero-label">A Fylle Internal Program</div>
          <h1>Where builders<br />make things <em>happen</em>.</h1>
          <p className="build-hero-sub">
            In the GenAI era, software is commodity.<br />
            <strong>GTM, execution & go-to-market</strong> is everything.
          </p>
        </div>
      </section>

      {/* Three Pillars */}
      <section className="build-pillars">
        <div className="build-container">
          <div className="build-section-label reveal">The Three Pillars</div>
          <div className="build-pillars-grid">
            <div className="build-pillar reveal">
              <div className="build-pillar-number">01</div>
              <span className="build-pillar-tag">Product</span>
              <h3>Fylle</h3>
              <p>The execution layer. The AI platform that enables production, generation and scaling of marketing processes for regulated industries.</p>
            </div>
            <div className="build-pillar reveal">
              <div className="build-pillar-number">02</div>
              <span className="build-pillar-tag">Lab</span>
              <h3>Fylle Service</h3>
              <p>The R&D lab where services become replicable packs. Body rental and competence center for network startups.</p>
            </div>
            <div className="build-pillar reveal">
              <div className="build-pillar-number">03</div>
              <span className="build-pillar-tag">Program</span>
              <h3>Fylle Build</h3>
              <p>Our team builds side-projects with Fylle stack and support. In return, Fylle enters with an equity stake from 1% to 5%.</p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works / The Deal */}
      <section className="build-how">
        <div className="build-container">
          <div className="build-section-label reveal">The Deal</div>
          <h2 className="build-how-headline reveal">You build. We accelerate.</h2>
          <p className="build-how-sub reveal">Fylle's stake is proportional to the level of support the project uses. Simple, transparent, aligned.</p>
          <div className="build-deal-tiers">
            <div className="build-tier reveal">
              <div className="build-tier-equity">1%</div>
              <div className="build-tier-label">Equity</div>
              <h4>Stack Only</h4>
              <ul>
                <li>Shared technology stack</li>
                <li>Optimized tool bundle</li>
                <li>Builder community</li>
              </ul>
            </div>
            <div className="build-tier build-tier-featured reveal">
              <div className="build-tier-equity">2-3%</div>
              <div className="build-tier-label">Equity</div>
              <h4>Stack + Service</h4>
              <ul>
                <li>Everything in Stack Only</li>
                <li>Fylle Service expertise</li>
                <li>Dedicated tech support</li>
                <li>Shared R&D</li>
              </ul>
            </div>
            <div className="build-tier reveal">
              <div className="build-tier-equity">4-5%</div>
              <div className="build-tier-label">Equity</div>
              <h4>Full Build</h4>
              <ul>
                <li>Everything in Stack + Service</li>
                <li>GTM & execution support</li>
                <li>Investor network</li>
                <li>Legal support via partners</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Revenue Streams */}
      <section className="build-revenue">
        <div className="build-container">
          <div className="build-section-label reveal">Revenue Streams</div>
          <h2 className="build-how-headline reveal" style={{ marginBottom: 0 }}>Three growth engines.</h2>
          <div className="build-revenue-grid">
            <div className="build-rev-card reveal">
              <span className="build-rev-num">Stream 01</span>
              <h4>Equity Portfolio</h4>
              <p>Micro-stakes in high-potential projects built by our team. Long-term, asymmetric by nature. One project that takes off pays for everything.</p>
            </div>
            <div className="build-rev-card reveal">
              <span className="build-rev-num">Stream 02</span>
              <h4>Body Rental & Fractional</h4>
              <p>Expertise developed internally — AI, automation, content — becomes a service for external startups. Recurring and predictable revenue.</p>
            </div>
            <div className="build-rev-card reveal">
              <span className="build-rev-num">Stream 03</span>
              <h4>Technology Bundle</h4>
              <p>Fylle as a cost center offering tool bundles for rent, optimizing costs for all network startups. Shared infrastructure.</p>
            </div>
          </div>
        </div>
      </section>

      {/* The Space / Hub */}
      <section className="build-space">
        <div className="build-container">
          <div className="build-space-content">
            <div className="reveal">
              <div className="build-section-label">The Space</div>
              <h2 className="build-space-headline">A place<br />for those<br />who <em>build</em>.</h2>
              <p className="build-space-desc">Not a coworking. Not an accelerator. A physical hub where builders find everything they need to go from zero to market, without noise.</p>
            </div>
            <div className="build-space-features reveal">
              <div className="build-space-feature">
                <div className="build-space-icon">⚡</div>
                <div>
                  <h4>Execution</h4>
                  <p>Direct support from the Fylle team and Service network</p>
                </div>
              </div>
              <div className="build-space-feature">
                <div className="build-space-icon">⚖️</div>
                <div>
                  <h4>Legal</h4>
                  <p>Access to legal partners specialized in startups</p>
                </div>
              </div>
              <div className="build-space-feature">
                <div className="build-space-icon">💰</div>
                <div>
                  <h4>Funding</h4>
                  <p>Network of advisors and partner investors</p>
                </div>
              </div>
              <div className="build-space-feature">
                <div className="build-space-icon">🛠️</div>
                <div>
                  <h4>Stack</h4>
                  <p>Shared technology bundle at optimized costs</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="build-cta">
        <div className="build-cta-glow"></div>
        <div className="build-container">
          <h2 className="reveal">Let's build<br />something.</h2>
          <p className="reveal">Selector is the first project. The next one is already on its way.</p>
          <button className="build-cta-button reveal" onClick={() => window.location.href = 'mailto:hello@fylle.ai?subject=Fylle%20Build'}>
            Let's Build →
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="build-footer">
        Fylle S.R.L. — Internal Document — 2025
      </footer>
    </div>
  )
}
