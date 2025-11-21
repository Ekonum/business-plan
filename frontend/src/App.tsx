import { useEffect, useMemo, useState } from 'react'
import { createEntity, fetchProjection } from './api'

interface MonthlyBreakdown {
  month: string
  revenue: number
  variable_costs: number
  fixed_costs: number
  amortization: number
  loan_interest: number
  loan_principal: number
  ebt: number
  cash: number
}

interface ProjectionResponse {
  periods: MonthlyBreakdown[]
  metadata: Record<string, string | null>
}

function formatMonthLabel(raw: string) {
  const d = new Date(raw)
  return d.toLocaleDateString('fr-FR', { month: 'short', year: 'numeric' })
}

const seedPayload = {
  offers: [
    { name: 'Forfait déploiement Odoo', offer_type: 'one_off', default_price: 12000 },
    { name: 'TMA mensuelle', offer_type: 'recurring', default_price: 2500 },
    { name: 'Licences Google Workspace', offer_type: 'license', default_price: 8, variable_cost_rate: 0.88 },
    { name: 'Achat / revente matériel', offer_type: 'hardware', default_price: 5000, variable_cost_rate: 0.75 }
  ],
  contracts: [
    { client_name: 'Client A', offer_name: 'Forfait déploiement Odoo', start_date: '2024-10-01', recurrence: 'one_time', total_value: 18000, quantity: 1, tax_rate: 0.2,
      payments: [
        { label: 'Acompte 40%', due_date: '2024-10-15', amount: 7200 },
        { label: 'Intermédiaire 40%', due_date: '2025-01-15', amount: 7200 },
        { label: 'Solde 20%', due_date: '2025-03-15', amount: 3600 }
      ]
    },
    { client_name: 'Client B', offer_name: 'TMA mensuelle', start_date: '2024-10-01', recurrence: 'monthly', total_value: 2500, quantity: 1, tax_rate: 0.2 },
    { client_name: 'Client C', offer_name: 'Licences Google Workspace', start_date: '2024-10-01', recurrence: 'monthly', total_value: 800, quantity: 1, tax_rate: 0.2 },
    { client_name: 'Client D', offer_name: 'Achat / revente matériel', start_date: '2024-11-01', recurrence: 'one_time', total_value: 7000, quantity: 1, tax_rate: 0.2,
      payments: [{ label: 'Paiement comptant', due_date: '2024-11-05', amount: 7000 }]
    }
  ],
  fixed_costs: [
    { name: 'Salaires & charges sociales', monthly_amount: 35000, start_date: '2024-10-01' },
    { name: 'Loyer', monthly_amount: 3500, start_date: '2024-10-01' },
    { name: 'Logiciels', monthly_amount: 1200, start_date: '2024-10-01' }
  ],
  assets: [
    { name: 'Serveurs', purchase_date: '2024-10-01', purchase_amount: 18000, amortization_months: 36 }
  ],
  loans: [
    { name: 'Prêt BPI', principal: 50000, annual_rate: 0.03, start_date: '2024-10-01', term_months: 36 }
  ]
}

function App() {
  const [startYear, setStartYear] = useState(2024)
  const [years, setYears] = useState(3)
  const [initialCash, setInitialCash] = useState(15000)
  const [projection, setProjection] = useState<ProjectionResponse | null>(null)
  const [status, setStatus] = useState<string>('')

  const cashRunway = useMemo(() => {
    if (!projection) return 0
    const negatives = projection.periods.findIndex((p) => p.cash < 0)
    return negatives === -1 ? projection.periods.length : negatives
  }, [projection])

  async function seedData() {
    setStatus('Chargement des hypothèses...')
    try {
      const createdOffers: Record<string, any> = {}
      // Create offers
      for (const offer of seedPayload.offers) {
        const created = await createEntity('offers', offer)
        createdOffers[offer.name] = created
      }
      // Contracts & payment plans
      for (const contract of seedPayload.contracts) {
        const createdOffer = createdOffers[contract.offer_name]
        const response = await createEntity('contracts', {
          client_name: contract.client_name,
          offer_id: createdOffer.id,
          start_date: contract.start_date,
          recurrence: contract.recurrence,
          total_value: contract.total_value,
          quantity: contract.quantity,
          tax_rate: contract.tax_rate
        })
        if (contract.payments) {
          for (const evt of contract.payments) {
            await createEntity('payments', { ...evt, contract_id: response.id })
          }
        }
      }
      for (const cost of seedPayload.fixed_costs) {
        await createEntity('fixed-costs', cost)
      }
      for (const asset of seedPayload.assets) {
        await createEntity('assets', asset)
      }
      for (const loan of seedPayload.loans) {
        await createEntity('loans', loan)
      }
      setStatus('Hypothèses injectées. Lancez la projection.')
    } catch (err) {
      console.error(err)
      setStatus('Erreur lors de l\'injection des données')
    }
  }

  async function runProjection() {
    setStatus('Calcul en cours...')
    try {
      const res = await fetchProjection(startYear, years, initialCash)
      setProjection(res)
      setStatus('Projection prête')
    } catch (err) {
      console.error(err)
      setStatus('Erreur lors du calcul de la projection')
    }
  }

  useEffect(() => {
    runProjection()
  }, [])

  return (
    <div className="app-shell">
      <h1>Ekonum · Pilotage financier</h1>
      <p>Construisez un budget multi-années, comparez budget vs réalisé et suivez votre trésorerie.</p>

      <div className="card grid two">
        <div>
          <h3>Paramètres fiscaux</h3>
          <label>Exercice de départ (année civile de début)</label>
          <input type="number" value={startYear} onChange={(e) => setStartYear(Number(e.target.value))} />
          <label>Nombre d'exercices (octobre → septembre)</label>
          <input type="number" value={years} min={1} max={10} onChange={(e) => setYears(Number(e.target.value))} />
          <label>Cash initial</label>
          <input type="number" value={initialCash} onChange={(e) => setInitialCash(Number(e.target.value))} />
          <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem' }}>
            <button onClick={runProjection}>Calculer la projection</button>
            <button className="secondary" onClick={seedData}>Charger des hypothèses type</button>
          </div>
          <p style={{ color: '#475569', marginTop: '0.75rem' }}>{status}</p>
        </div>
        <div>
          <h3>Architecture fonctionnelle</h3>
          <ul>
            <li>Catalogue d'offres (forfaits, récurrents, licences, matériel).</li>
            <li>Contrats reliés aux offres, échéances de paiement ou facturation automatique.</li>
            <li>Charges fixes, immobilisations (amortissement mensuel), emprunts (échéancier).</li>
            <li>Projection P&L + trésorerie, comparaisons budget vs réalisé (imports à venir).</li>
          </ul>
          <p><span className="badge">Runway cash</span> {cashRunway} mois avant tension.</p>
        </div>
      </div>

      <div className="card">
        <h3>P&L et cash mensuel</h3>
        {projection ? (
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Mois</th>
                  <th>CA</th>
                  <th>Coûts variables</th>
                  <th>Charges fixes</th>
                  <th>Amortissements</th>
                  <th>Intérêts</th>
                  <th>Capital</th>
                  <th>Résultat</th>
                  <th>Cash fin de mois</th>
                </tr>
              </thead>
              <tbody>
                {projection.periods.map((p) => (
                  <tr key={p.month}>
                    <td>{formatMonthLabel(p.month)}</td>
                    <td>{p.revenue.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</td>
                    <td>{p.variable_costs.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</td>
                    <td>{p.fixed_costs.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</td>
                    <td>{p.amortization.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</td>
                    <td>{p.loan_interest.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</td>
                    <td>{p.loan_principal.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</td>
                    <td>{p.ebt.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</td>
                    <td>{p.cash.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>Configurez vos paramètres et lancez une projection.</p>
        )}
      </div>
    </div>
  )
}

export default App
