'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BellOff, CheckCheck, Megaphone } from 'lucide-react';

import { EntetePage } from '@/components/layout/entete-page';
import {
  Badge,
  Bouton,
  Carte,
  Chargement,
  CorpsCarte,
  EnteteCarte,
  EtatVide,
  MessageErreur,
} from '@/components/ui/primitives';
import { useAccessibilite } from '@/lib/accessibilite';
import { api } from '@/lib/api';
import { formaterDate, formaterDateHeure, humaniser } from '@/lib/utils';

interface Notification {
  id: string;
  type: string;
  titre: string;
  message: string;
  message_simplifie: string | null;
  pictogramme: string | null;
  priorite: number;
  lien: string | null;
  lue: boolean;
  date: string;
}

interface Annonce {
  id: string;
  titre: string;
  contenu: string;
  contenu_simplifie: string | null;
  urgente: boolean;
  date_publication: string;
  nombre_vues: number;
}

export default function PageNotifications() {
  const { modeSimplifie } = useAccessibilite();
  const client = useQueryClient();

  const notifications = useQuery({
    queryKey: ['notifications'],
    queryFn: () =>
      api.get<{ non_lues: number; notifications: Notification[] }>(
        '/communication/notifications',
        { limite: 100 },
      ),
  });

  const annonces = useQuery({
    queryKey: ['annonces'],
    queryFn: () => api.get<Annonce[]>('/communication/annonces'),
  });

  const marquerLues = useMutation({
    mutationFn: () => api.post('/communication/notifications/marquer-lues'),
    onSuccess: () => client.invalidateQueries({ queryKey: ['notifications'] }),
  });

  if (notifications.isLoading) return <Chargement libelle="Chargement de vos notifications…" />;
  if (notifications.isError) return <MessageErreur erreur={notifications.error} />;

  const donnees = notifications.data!;

  return (
    <>
      <EntetePage
        titre="Notifications et annonces"
        description={`${donnees.non_lues} notification(s) non lue(s).`}
        actions={
          donnees.non_lues > 0 ? (
            <Bouton
              variante="secondaire"
              onClick={() => marquerLues.mutate()}
              chargement={marquerLues.isPending}
              icone={<CheckCheck size={17} aria-hidden />}
            >
              Tout marquer comme lu
            </Bouton>
          ) : null
        }
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_24rem]">
        <Carte>
          <EnteteCarte titre="Mes notifications" />
          {donnees.notifications.length > 0 ? (
            <ul className="divide-y">
              {donnees.notifications.map((notification) => (
                <li
                  key={notification.id}
                  className={`flex gap-3 px-5 py-4 ${notification.lue ? '' : 'bg-[rgb(var(--accent))]/5'}`}
                >
                  <span aria-hidden className="mt-0.5 shrink-0 text-xl">
                    {notification.pictogramme ?? '🔔'}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="flex flex-wrap items-center gap-2 font-medium">
                      {notification.titre}
                      {!notification.lue ? <Badge ton="info">Nouveau</Badge> : null}
                      {notification.priorite >= 3 ? <Badge ton="danger">Urgent</Badge> : null}
                    </p>
                    <p className="mt-0.5 text-sm texte-doux">
                      {modeSimplifie && notification.message_simplifie
                        ? notification.message_simplifie
                        : notification.message}
                    </p>
                    <p className="mt-1 text-xs texte-doux">
                      {humaniser(notification.type)} · {formaterDateHeure(notification.date)}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <EtatVide
              titre="Aucune notification"
              description="Vous serez averti ici des résultats, bulletins, convocations et échéances."
              icone={<BellOff size={32} aria-hidden />}
            />
          )}
        </Carte>

        <Carte className="h-fit">
          <EnteteCarte
            titre={
              <span className="flex items-center gap-2">
                <Megaphone size={19} aria-hidden /> Annonces officielles
              </span>
            }
          />
          {(annonces.data ?? []).length > 0 ? (
            <ul className="divide-y">
              {(annonces.data ?? []).map((annonce) => (
                <li key={annonce.id} className="px-5 py-4">
                  <p className="flex flex-wrap items-center gap-2 font-medium">
                    {annonce.titre}
                    {annonce.urgente ? <Badge ton="danger">Urgent</Badge> : null}
                  </p>
                  <p className="mt-1 text-sm texte-doux">
                    {modeSimplifie && annonce.contenu_simplifie
                      ? annonce.contenu_simplifie
                      : annonce.contenu}
                  </p>
                  <p className="mt-1.5 text-xs texte-doux">
                    Publiée le {formaterDate(annonce.date_publication)}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <CorpsCarte>
              <p className="text-sm texte-doux">Aucune annonce en cours.</p>
            </CorpsCarte>
          )}
        </Carte>
      </div>
    </>
  );
}
