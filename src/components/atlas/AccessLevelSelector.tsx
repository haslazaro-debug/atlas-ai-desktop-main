import React, { useState } from 'react';
import { Check, Sparkles, Zap, Shield, Crown } from 'lucide-react';

interface AccessLevelSelectorProps {
  currentTier?: string;
}

const TIERS = [
  {
    id: 'standard',
    name: 'Standard',
    price: '$29',
    period: '/mo',
    description: 'Managed access with Haiku 4.5. Great for personal daily tasks.',
    features: ['5M tokens/mo quota', 'All 5 Killer Scenarios', 'Sentinel monitoring', 'Standard support'],
    planKey: 'standard',
    icon: Zap,
    badge: null,
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '$99',
    period: '/mo',
    description: 'Powered by Sonnet 5 for heavy reasoning and vision workflows.',
    features: ['8M tokens/mo quota (Hard cap)', 'Priority request queue', 'Early access to new scenarios', 'Priority support'],
    planKey: 'pro',
    icon: Sparkles,
    badge: 'Popular',
  },
  {
    id: 'business',
    name: 'Business',
    price: '$189',
    period: '/mo',
    description: 'For power users and teams requiring maximum throughput.',
    features: ['15M tokens/mo quota', 'Max priority queue', 'Advanced telemetry & features', 'Dedicated assistance'],
    planKey: 'business',
    icon: Crown,
    badge: null,
  },
  {
    id: 'lifetime_standard',
    name: 'Lifetime Standard',
    price: '$349',
    period: 'one-time',
    description: 'BYOK license. Zero recurring token costs on our infrastructure.',
    features: ['Bring Your Own Key (BYOK)', 'Lifetime software updates', 'All Killer Scenarios included', 'Community support'],
    planKey: 'lifetime_standard',
    icon: Shield,
    badge: 'Best Value',
  },
  {
    id: 'lifetime_pro',
    name: 'Lifetime Pro',
    price: '$599',
    period: 'one-time',
    description: 'Ultimate BYOK tier with a massive first-year managed boost.',
    features: ['BYOK + 10M Managed Boost (Year 1)', 'Lifetime VIP priority support', 'All future features included', 'Early access pass'],
    planKey: 'lifetime_pro',
    icon: Crown,
    badge: 'Ultimate',
  },
];

export const AccessLevelSelector: React.FC<AccessLevelSelectorProps> = ({ currentTier = 'standard' }) => {
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);

  const handleCheckout = async (planKey: string) => {
    try {
      setLoadingPlan(planKey);
      const res = await fetch('http://127.0.0.1:8080/api/create-checkout-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan: planKey }),
      });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      } else {
        alert(data.error || 'Failed to create checkout session');
      }
    } catch (err) {
      console.error(err);
      alert('Network error while connecting to Stripe');
    } finally {
      setLoadingPlan(null);
    }
  };

  return (
    <div className="w-full py-4 px-2 max-h-[70vh] overflow-y-auto">
      <div className="text-center mb-6">
        <h3 className="text-xl font-semibold text-white tracking-tight">Choose Your Access Tier</h3>
        <p className="text-sm text-zinc-400 mt-1">Unlock full automation, advanced models, and robust limits.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pb-6">
        {TIERS.map((tier) => {
          const Icon = tier.icon;
          const isCurrent = currentTier === tier.id;
          const isLifetime = tier.id.startsWith('lifetime');

          return (
            <div
              key={tier.id}
              className={`relative flex flex-col justify-between rounded-xl p-5 border transition-all ${
                isCurrent
                  ? 'bg-zinc-900/90 border-emerald-500/50 shadow-lg shadow-emerald-500/10'
                  : 'bg-zinc-950/60 border-zinc-800/80 hover:border-zinc-700'
              }`}
            >
              {tier.badge && (
                <span className="absolute -top-2.5 right-4 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full">
                  {tier.badge}
                </span>
              )}

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="p-2 rounded-lg bg-zinc-800/50 text-zinc-300">
                    <Icon className="w-4 h-4" />
                  </div>
                  <h4 className="font-medium text-white">{tier.name}</h4>
                </div>

                <div className="flex items-baseline gap-1 my-3">
                  <span className="text-2xl font-bold text-white">{tier.price}</span>
                  <span className="text-xs text-zinc-400">{tier.period}</span>
                </div>

                <p className="text-xs text-zinc-400 mb-4 min-h-[32px]">{tier.description}</p>

                <ul className="space-y-2 mb-6">
                  {tier.features.map((feat, idx) => (
                    <li key={idx} className="flex items-center gap-2 text-xs text-zinc-300">
                      <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span>{feat}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <button
                onClick={() => handleCheckout(tier.planKey)}
                disabled={isCurrent || loadingPlan === tier.planKey}
                className={`w-full py-2.5 px-4 rounded-lg font-medium text-xs transition-all flex items-center justify-center gap-2 ${
                  isCurrent
                    ? 'bg-zinc-800 text-zinc-500 cursor-default'
                    : isLifetime
                    ? 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-md'
                    : 'bg-zinc-100 hover:bg-white text-zinc-900'
                }`}
              >
                {loadingPlan === tier.planKey ? (
                  'Preparing Stripe...'
                ) : isCurrent ? (
                  'Active Plan'
                ) : isLifetime ? (
                  `Get ${tier.name}`
                ) : (
                  `Subscribe to ${tier.name}`
                )}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
