'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { Accessibility, ArrowRight, Compass, KeyRound, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import { ListeDescriptive } from '@/components/ui/donnees';
import {
  Badge,
  Bouton,
  Carte,
  Champ,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  Interrupteur,
  MessageErreur,
} from '@/components/ui/primitives';
import { useAccessibilite } from '@/lib/accessibilite';
import { api } from '@/lib/api';
import { useSession } from '@/lib/session';
import { formaterDateHeure, humaniser } from '@/lib/utils';

/**
 * Correspondance entre les raccourcis renvoyés par l'API — qui désignent des
 * points d'entrée du service — et les écrans qui les présentent.
 */
const ECRANS: Record<string, string> = {
  '/tableaux-de-bord/national': '/tableau-de-bord',
  '/recherche/avancee': '/recherche',
  '/sessions': '/examens',
  '/etablissements-carte/points': '/cartographie',
  '/etablissements': '/etablissements',
  '/classes': '/classes',
  '/apprenants': '/apprenants',
  '/enseignants': '/enseignants',
  '/candidats': '/candidats',
  '/bulletins': '/bulletins',
  '/evaluations': '/evaluations',
  '/bourses': '/bourses',
  '/notifications': '/notifications',
};

interface MonEspace {
  utilisateur: string;
  roles: string[];
  niveau: string;
  raccourcis: Array<{ libelle: string; lien: string }>;
}

export default function PageProfil() {
  const { utilisateur, chargement, rafraichirProfil } = useSession();
  const accessibilite = useAccessibilite();

  const espace = useQuery({
    queryKey: ['mon-espace'],
    queryFn: () => api.get<MonEspace>('/tableaux-de-bord/mon-espace'),
  });

  const [ancien, setAncien] = useState('');
  const [nouveau, setNouveau] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [message, setMessage] = useState<string | null>(null);

  const changement = useMutation({
    mutationFn: () =>
      api.post('/auth/moi/mot-de-passe', {
        ancien_mot_de_passe: ancien,
        nouveau_mot_de_passe: nouveau,
      }),
    onSuccess: () => {
      setMessage('Mot de passe modifié. Vous devrez vous reconnecter.');
      setAncien('');
      setNouveau('');
      setConfirmation('');
    },
  });

  const preferences = useMutation({
    mutationFn: (charge: Record<string, unknown>) => api.patch('/auth/moi/accessibilite', charge),
    onSuccess: () => void rafraichirProfil(),
  });

  if (chargement) return <Chargement />;
  if (!utilisateur) return null;

  const motsDePasseDifferents = nouveau !== '' && confirmation !== '' && nouveau !== confirmation;

  return (
    <>
      <EntetePage
        titre="Mon profil"
        description="Vos informations, vos droits et vos préférences d'accessibilité."
      />

      <Carte className="mb-4">
        <EnteteCarte
          titre={
            <span className="flex items-center gap-2">
              <Compass size={19} aria-hidden /> Mon espace
            </span>
          }
          description={
            espace.data
              ? `Périmètre ${humaniser(espace.data.niveau).toLowerCase()} — les écrans ci-dessous correspondent à vos droits.`
              : 'Écrans ouverts par vos rôles.'
          }
        />
        <CorpsCarte>
          {espace.isLoading ? (
            <Chargement libelle="Chargement de votre espace…" />
          ) : (espace.data?.raccourcis ?? []).length === 0 ? (
            <p className="text-sm texte-doux">
              Aucun raccourci proposé : vos droits ne couvrent pas d&apos;écran de pilotage.
            </p>
          ) : (
            <ul className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
              {(espace.data?.raccourcis ?? []).map((raccourci) => {
                const cible = ECRANS[raccourci.lien];
                return (
                  <li key={raccourci.lien}>
                    {cible ? (
                      <Link
                        href={cible}
                        className="surface-douce flex items-center justify-between gap-2 rounded-lg px-4 py-3 text-sm font-medium hover:bg-[rgb(var(--fond-doux))]"
                      >
                        {raccourci.libelle}
                        <ArrowRight size={16} aria-hidden />
                      </Link>
                    ) : (
                      <span className="surface-douce flex rounded-lg px-4 py-3 text-sm texte-doux">
                        {raccourci.libelle}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </CorpsCarte>
      </Carte>

      <div className="grid gap-4 xl:grid-cols-3">
        <Carte className="xl:col-span-2">
          <EnteteCarte titre="Identité" />
          <CorpsCarte>
            <ListeDescriptive
              colonnes={2}
              entrees={[
                { terme: 'Nom complet', valeur: utilisateur.nom_complet },
                { terme: 'Adresse électronique', valeur: utilisateur.email },
                { terme: 'Téléphone', valeur: utilisateur.telephone ?? '—' },
                {
                  terme: 'Dernière connexion',
                  valeur: formaterDateHeure(utilisateur.derniere_connexion),
                },
                { terme: 'Langue', valeur: utilisateur.langue },
                {
                  terme: 'Besoin spécifique déclaré',
                  valeur: humaniser(utilisateur.type_handicap),
                },
              ]}
            />
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <ShieldCheck size={19} aria-hidden /> Droits
              </span>
            }
            description={`Portée : ${humaniser(utilisateur.niveau_scope)}.`}
          />
          <CorpsCarte>
            <p className="mb-2 text-sm font-medium texte-doux">Rôles</p>
            <ul className="mb-4 flex flex-wrap gap-1.5">
              {utilisateur.roles.map((role) => (
                <li key={role}>
                  <Badge ton="info">{role}</Badge>
                </li>
              ))}
            </ul>
            <p className="text-sm texte-doux">
              {utilisateur.permissions.length} permission(s) effective(s).
            </p>
          </CorpsCarte>
        </Carte>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <Accessibility size={19} aria-hidden /> Préférences enregistrées
              </span>
            }
            description="Ces réglages suivent votre compte, quel que soit le poste utilisé."
          />
          <CorpsCarte className="space-y-2">
            <Interrupteur
              etiquette="Interface simplifiée"
              description="Pictogrammes et libellés courts"
              actif={utilisateur.mode_simplifie}
              onChange={() => {
                preferences.mutate({ mode_simplifie: !utilisateur.mode_simplifie });
                accessibilite.definir('modeSimplifie', !utilisateur.mode_simplifie);
              }}
            />
            <Interrupteur
              etiquette="Contraste élevé"
              actif={utilisateur.contraste_eleve}
              onChange={() => {
                preferences.mutate({ contraste_eleve: !utilisateur.contraste_eleve });
                accessibilite.definir(
                  'contraste',
                  utilisateur.contraste_eleve ? 'normal' : 'eleve',
                );
              }}
            />
            <Interrupteur
              etiquette="Grande police"
              actif={utilisateur.grande_police}
              onChange={() => {
                preferences.mutate({ grande_police: !utilisateur.grande_police });
                accessibilite.definir('police', utilisateur.grande_police ? 'normale' : 'grande');
              }}
            />
            <Interrupteur
              etiquette="Lecture vocale"
              description="Écouter les chiffres, bulletins et résultats"
              actif={utilisateur.lecture_vocale}
              onChange={() => {
                preferences.mutate({ lecture_vocale: !utilisateur.lecture_vocale });
                accessibilite.definir('lectureVocale', !utilisateur.lecture_vocale);
              }}
            />
          </CorpsCarte>
        </Carte>

        <Carte>
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <KeyRound size={19} aria-hidden /> Changer mon mot de passe
              </span>
            }
          />
          <CorpsCarte>
            <form
              onSubmit={(evenement) => {
                evenement.preventDefault();
                if (!motsDePasseDifferents) changement.mutate();
              }}
              className="space-y-4"
            >
              <Champ
                etiquette="Mot de passe actuel"
                type="password"
                autoComplete="current-password"
                required
                value={ancien}
                onChange={(evenement) => setAncien(evenement.target.value)}
              />
              <Champ
                etiquette="Nouveau mot de passe"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={nouveau}
                onChange={(evenement) => setNouveau(evenement.target.value)}
                aide="Au moins huit caractères, mêlant lettres et chiffres."
              />
              <Champ
                etiquette="Confirmer le nouveau mot de passe"
                type="password"
                autoComplete="new-password"
                required
                value={confirmation}
                onChange={(evenement) => setConfirmation(evenement.target.value)}
                erreur={motsDePasseDifferents ? 'Les deux saisies diffèrent.' : undefined}
              />

              {changement.isError ? <MessageErreur erreur={changement.error} /> : null}
              {message ? (
                <p
                  role="status"
                  className="rounded-lg border border-[rgb(var(--succes))]/40 bg-[rgb(var(--succes))]/8 px-3 py-2.5 text-sm font-medium"
                >
                  {message}
                </p>
              ) : null}

              <Bouton type="submit" chargement={changement.isPending} disabled={motsDePasseDifferents}>
                Modifier le mot de passe
              </Bouton>
            </form>
          </CorpsCarte>
        </Carte>
      </div>
    </>
  );
}
