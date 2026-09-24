'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Inbox, Send } from 'lucide-react';
import { useState } from 'react';

import { EntetePage } from '@/components/layout/entete-page';
import {
  Badge,
  Carte,
  Champ,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  MessageErreur,
} from '@/components/ui/primitives';
import { api, type Page } from '@/lib/api';
import { formaterDateHeure, initiales, tronquer } from '@/lib/utils';
import type { Utilisateur } from '@/types/api';

interface Message {
  id: string;
  conversation_id: string;
  objet: string | null;
  corps: string;
  recu: boolean;
  lu: boolean;
  date: string;
}

export default function PageMessagerie() {
  const client = useQueryClient();
  const [destinataire, setDestinataire] = useState('');
  const [objet, setObjet] = useState('');
  const [corps, setCorps] = useState('');
  const [confirmation, setConfirmation] = useState<string | null>(null);

  const messages = useQuery({
    queryKey: ['messages'],
    queryFn: () => api.get<Message[]>('/communication/messages', { limite: 100 }),
  });

  // La liste des destinataires possibles reste volontairement courte : on
  // s'appuie sur la recherche plutôt que sur un annuaire exhaustif.
  const utilisateurs = useQuery({
    queryKey: ['utilisateurs-messagerie', destinataire],
    enabled: destinataire.length >= 3,
    queryFn: () => api.get<Page<Utilisateur>>('/utilisateurs', { q: destinataire, size: 6 }),
  });

  const envoi = useMutation({
    mutationFn: (destinataireId: string) =>
      api.post('/communication/messages', undefined, {
        parametres: {
          destinataire_id: destinataireId,
          objet: objet || undefined,
          corps,
        },
      }),
    onSuccess: () => {
      setConfirmation('Message envoyé.');
      setObjet('');
      setCorps('');
      setDestinataire('');
      void client.invalidateQueries({ queryKey: ['messages'] });
    },
  });

  if (messages.isLoading) return <Chargement libelle="Chargement de votre messagerie…" />;
  if (messages.isError) return <MessageErreur erreur={messages.error} />;

  const liste = messages.data ?? [];
  const recus = liste.filter((message) => message.recu);
  const envoyes = liste.filter((message) => !message.recu);
  const candidats = utilisateurs.data?.items ?? [];

  return (
    <>
      <EntetePage
        titre="Messagerie"
        description="Échanges entre apprenants, enseignants, parents, établissements et administrations."
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_24rem]">
        <div className="space-y-4">
          <Carte>
            <EnteteCarte
              titre={
                <span className="flex items-center gap-2">
                  <Inbox size={19} aria-hidden /> Messages reçus
                </span>
              }
              description={`${recus.length} message(s).`}
            />
            {recus.length > 0 ? (
              <ul className="divide-y">
                {recus.map((message) => (
                  <li
                    key={message.id}
                    className={`px-5 py-4 ${message.lu ? '' : 'bg-[rgb(var(--accent))]/5'}`}
                  >
                    <p className="flex flex-wrap items-center gap-2 font-medium">
                      {message.objet ?? 'Sans objet'}
                      {!message.lu ? <Badge ton="info">Non lu</Badge> : null}
                    </p>
                    <p className="mt-0.5 text-sm texte-doux">{tronquer(message.corps, 180)}</p>
                    <p className="mt-1 text-xs texte-doux">{formaterDateHeure(message.date)}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <EtatVide
                titre="Aucun message reçu"
                description="Vos échanges avec les enseignants et l'administration apparaîtront ici."
                icone={<Inbox size={32} aria-hidden />}
              />
            )}
          </Carte>

          {envoyes.length > 0 ? (
            <Carte>
              <EnteteCarte
                titre={
                  <span className="flex items-center gap-2">
                    <Send size={19} aria-hidden /> Messages envoyés
                  </span>
                }
                description={`${envoyes.length} message(s).`}
              />
              <ul className="divide-y">
                {envoyes.map((message) => (
                  <li key={message.id} className="px-5 py-4">
                    <p className="font-medium">{message.objet ?? 'Sans objet'}</p>
                    <p className="mt-0.5 text-sm texte-doux">{tronquer(message.corps, 180)}</p>
                    <p className="mt-1 text-xs texte-doux">{formaterDateHeure(message.date)}</p>
                  </li>
                ))}
              </ul>
            </Carte>
          ) : null}
        </div>

        <Carte className="h-fit">
          <EnteteCarte titre="Nouveau message" />
          <CorpsCarte className="space-y-4">
            <Champ
              etiquette="Destinataire"
              value={destinataire}
              onChange={(evenement) => setDestinataire(evenement.target.value)}
              placeholder="Nom ou adresse électronique"
              aide="Saisissez au moins trois caractères pour rechercher."
            />

            {candidats.length > 0 ? (
              <ul className="space-y-1.5" aria-label="Destinataires proposés">
                {candidats.map((utilisateur) => (
                  <li key={utilisateur.id}>
                    <button
                      type="button"
                      onClick={() => {
                        if (corps.trim().length > 0) envoi.mutate(utilisateur.id);
                      }}
                      disabled={corps.trim().length === 0 || envoi.isPending}
                      className="flex w-full items-center gap-2.5 rounded-lg border px-3 py-2 text-left transition hover:bg-[rgb(var(--fond-doux))] disabled:opacity-55"
                    >
                      <span
                        aria-hidden
                        className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[rgb(var(--accent))]/15 text-xs font-semibold text-[rgb(var(--accent))]"
                      >
                        {initiales(utilisateur.nom_complet)}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium">
                          {utilisateur.nom_complet}
                        </span>
                        <span className="block truncate text-xs texte-doux">
                          {utilisateur.email}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}

            <Champ
              etiquette="Objet"
              value={objet}
              onChange={(evenement) => setObjet(evenement.target.value)}
              placeholder="Objet du message"
            />

            <div className="space-y-1.5">
              <label htmlFor="corps-message" className="block text-sm font-medium">
                Message
              </label>
              <textarea
                id="corps-message"
                rows={5}
                value={corps}
                onChange={(evenement) => setCorps(evenement.target.value)}
                placeholder="Votre message…"
                className="w-full rounded-lg border bg-[rgb(var(--fond-carte))] px-3 py-2.5"
              />
            </div>

            <p className="text-xs texte-doux">
              Rédigez votre message, puis choisissez un destinataire dans la liste ci-dessus pour
              l&apos;envoyer.
            </p>

            {envoi.isError ? <MessageErreur erreur={envoi.error} /> : null}
            {confirmation ? (
              <p
                role="status"
                className="rounded-lg border border-[rgb(var(--succes))]/40 bg-[rgb(var(--succes))]/8 px-3 py-2.5 text-sm font-medium"
              >
                {confirmation}
              </p>
            ) : null}
          </CorpsCarte>
        </Carte>
      </div>
    </>
  );
}
