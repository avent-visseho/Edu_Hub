'use client';

import { useQuery } from '@tanstack/react-query';
import { Leaf, UtensilsCrossed } from 'lucide-react';
import { useMemo } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { Indicateur } from '@/components/ui/donnees';
import {
  Badge,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  MessageErreur,
} from '@/components/ui/primitives';
import { api } from '@/lib/api';
import { formaterNombre } from '@/lib/utils';

interface Menu {
  id: string;
  restaurant_id: string;
  date_service: string;
  service: string;
  entree: string | null;
  plat_principal: string;
  accompagnement: string | null;
  dessert: string | null;
  boisson: string | null;
  calories: number | null;
  vegetarien: boolean;
}

/** Regroupe les menus par jour, du plus proche au plus lointain. */
function grouperParJour(menus: Menu[]): Array<[string, Menu[]]> {
  const groupes = new Map<string, Menu[]>();
  for (const menu of menus) {
    const liste = groupes.get(menu.date_service) ?? [];
    liste.push(menu);
    groupes.set(menu.date_service, liste);
  }
  return Array.from(groupes.entries()).sort(([a], [b]) => a.localeCompare(b));
}

export default function PageRestauration() {
  const menus = useQuery({
    queryKey: ['menus'],
    queryFn: () => api.get<Menu[]>('/restauration/menus'),
  });

  const jours = useMemo(() => grouperParJour(menus.data ?? []), [menus.data]);

  if (menus.isLoading) return <Chargement libelle="Chargement des menus…" />;
  if (menus.isError) return <MessageErreur erreur={menus.error} />;

  const liste = menus.data ?? [];
  const vegetariens = liste.filter((menu) => menu.vegetarien).length;
  const caloriesMoyennes = liste.length
    ? liste.reduce((total, menu) => total + (menu.calories ?? 0), 0) / liste.length
    : 0;

  const formatterJour = new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  });

  return (
    <>
      <EntetePage
        titre="Restauration"
        description="Menus des restaurants universitaires et des cantines scolaires, pour les deux semaines à venir."
      />

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Indicateur
          libelle="Menus publiés"
          valeur={liste.length}
          icone={<UtensilsCrossed size={18} />}
          pictogramme="🍽️"
        />
        <Indicateur libelle="Jours couverts" valeur={jours.length} pictogramme="📅" />
        <Indicateur libelle="Options végétariennes" valeur={vegetariens} pictogramme="🥗" />
        <Indicateur
          libelle="Apport moyen"
          valeur={formaterNombre(caloriesMoyennes)}
          unite="kcal"
          pictogramme="⚡"
        />
      </div>

      {jours.length === 0 ? (
        <Carte>
          <EtatVide
            titre="Aucun menu publié"
            description="Les menus des prochains jours apparaîtront ici."
            icone={<UtensilsCrossed size={32} aria-hidden />}
          />
        </Carte>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {jours.map(([jour, menusDuJour]) => (
            <Carte key={jour}>
              <EnteteCarte
                titre={
                  <span className="text-base capitalize">
                    {formatterJour.format(new Date(jour))}
                  </span>
                }
              />
              <CorpsCarte className="space-y-4 p-4">
                {menusDuJour.map((menu) => (
                  <article key={menu.id}>
                    <p className="mb-1.5 flex flex-wrap items-center gap-2">
                      <Badge ton="neutre">{menu.service}</Badge>
                      {menu.vegetarien ? (
                        <Badge ton="succes">
                          <Leaf size={13} aria-hidden /> Végétarien
                        </Badge>
                      ) : null}
                      {menu.calories ? (
                        <span className="text-xs texte-doux">{menu.calories} kcal</span>
                      ) : null}
                    </p>
                    <dl className="space-y-1 text-sm">
                      {[
                        { terme: 'Entrée', valeur: menu.entree },
                        { terme: 'Plat', valeur: menu.plat_principal },
                        { terme: 'Accompagnement', valeur: menu.accompagnement },
                        { terme: 'Dessert', valeur: menu.dessert },
                        { terme: 'Boisson', valeur: menu.boisson },
                      ]
                        .filter((ligne) => ligne.valeur)
                        .map((ligne) => (
                          <div key={ligne.terme} className="flex gap-2">
                            <dt className="w-32 shrink-0 texte-doux">{ligne.terme}</dt>
                            <dd className="min-w-0 font-medium">{ligne.valeur}</dd>
                          </div>
                        ))}
                    </dl>
                  </article>
                ))}
              </CorpsCarte>
            </Carte>
          ))}
        </div>
      )}
    </>
  );
}
