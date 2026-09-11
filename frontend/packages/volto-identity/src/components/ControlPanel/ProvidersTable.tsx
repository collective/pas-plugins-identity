/**
 * The providers control panel's list.
 *
 * One row per provider, in the order the login page offers their buttons, and
 * dragged by a handle to change that order. What the list does with a drop is
 * its caller's business: it reports the new order, and saving it -- or putting
 * the row back when that fails -- happens in the panel.
 *
 * The drag library is one of Volto's lazy libraries, so the list first renders
 * without it, on the server and on the client until it has loaded, and each
 * row gains its handle once it has. Nothing but the handles waits for it.
 * @module components/ControlPanel/ProvidersTable
 */
import React from 'react';
import type { CSSProperties, ReactNode, Ref } from 'react';
import { Link } from 'react-router-dom';
import { Button, Table } from 'semantic-ui-react';
import { defineMessages, useIntl } from 'react-intl';

import Icon from '@plone/volto/components/theme/Icon/Icon';
import { useLazyLibs } from '@plone/volto/helpers/Loadable/Loadable';

import deleteSVG from '@plone/volto/icons/delete.svg';
import dragSVG from '@plone/volto/icons/drag.svg';
import pencilSVG from '@plone/volto/icons/pencil.svg';
import worldSVG from '@plone/volto/icons/world.svg';

import { providerEditUrl } from '../../config/routes';
import { movedIds } from '../../helpers/providerOrder';
import type { ConfiguredProvider } from '../../types';

/** The lazy libraries dragging a row needs. */
export const DND_LIBRARIES = [
  'dndKitCore',
  'dndKitSortable',
  'dndKitUtilities',
];

const messages = defineMessages({
  columnOrder: { id: 'Order', defaultMessage: 'Order' },
  columnTitle: { id: 'Title', defaultMessage: 'Title' },
  columnId: { id: 'Id', defaultMessage: 'Id' },
  columnDriver: { id: 'Driver', defaultMessage: 'Driver' },
  columnEnabled: { id: 'Enabled', defaultMessage: 'Enabled' },
  columnLogin: { id: 'Login screen', defaultMessage: 'Login screen' },
  columnActions: { id: 'Actions', defaultMessage: 'Actions' },
  yes: { id: 'Yes', defaultMessage: 'Yes' },
  no: { id: 'No', defaultMessage: 'No' },
  move: { id: 'Move {title}', defaultMessage: 'Move {title}' },
  edit: { id: 'Edit', defaultMessage: 'Edit' },
  test: { id: 'Test connection', defaultMessage: 'Test connection' },
  delete: { id: 'Delete', defaultMessage: 'Delete' },
});

type Props = {
  /** The providers, in the order to show them. */
  providers: ConfiguredProvider[];
  /** Given every provider's id, in the new order, when a row is dropped. */
  onReorder: (providerIds: string[]) => void;
  onTest: (provider: ConfiguredProvider) => void;
  onDelete: (provider: ConfiguredProvider) => void;
};

/** The loaded libraries, keyed as `config.settings.loadables` names them. */
type Libraries = Record<string, any>;

type RowProps = Pick<Props, 'onTest' | 'onDelete'> & {
  provider: ConfiguredProvider;
};

/** The table around the rows, which is the same whether or not they drag. */
const Frame = ({ children }: { children: ReactNode }) => {
  const intl = useIntl();
  return (
    <Table selectable compact>
      <Table.Header>
        <Table.Row>
          <Table.HeaderCell
            collapsing
            aria-label={intl.formatMessage(messages.columnOrder)}
          />
          <Table.HeaderCell>
            {intl.formatMessage(messages.columnTitle)}
          </Table.HeaderCell>
          <Table.HeaderCell>
            {intl.formatMessage(messages.columnId)}
          </Table.HeaderCell>
          <Table.HeaderCell>
            {intl.formatMessage(messages.columnDriver)}
          </Table.HeaderCell>
          <Table.HeaderCell>
            {intl.formatMessage(messages.columnEnabled)}
          </Table.HeaderCell>
          <Table.HeaderCell>
            {intl.formatMessage(messages.columnLogin)}
          </Table.HeaderCell>
          <Table.HeaderCell textAlign="right">
            {intl.formatMessage(messages.columnActions)}
          </Table.HeaderCell>
        </Table.Row>
      </Table.Header>
      <Table.Body>{children}</Table.Body>
    </Table>
  );
};

/**
 * One provider's row.
 *
 * A plain `tr` rather than Semantic's `Table.Row`, which does not pass a ref
 * on: the drag library measures the row's own node.
 */
const ProviderRow = ({
  provider,
  onTest,
  onDelete,
  handle = null,
  rowRef,
  style,
  dragging = false,
}: RowProps & {
  handle?: ReactNode;
  rowRef?: Ref<HTMLTableRowElement>;
  style?: CSSProperties;
  dragging?: boolean;
}) => {
  const intl = useIntl();
  const yesNo = (value: boolean) =>
    intl.formatMessage(value ? messages.yes : messages.no);
  return (
    <tr
      ref={rowRef}
      style={style}
      data-provider={provider.id}
      className={dragging ? 'identity-controlpanel__dragging' : undefined}
    >
      <td className="collapsing">{handle}</td>
      <td>{provider.title || provider.id}</td>
      <td>
        <code>{provider.id}</code>
      </td>
      <td>{provider.driver}</td>
      <td>{yesNo(provider.enabled)}</td>
      <td>{yesNo(provider.show_in_login)}</td>
      <td className="right aligned">
        {/* A link rather than a button: the edit form is a route, so it can
            be opened in a new tab. */}
        <Button
          as={Link}
          to={providerEditUrl(provider.id)}
          basic
          icon
          aria-label={intl.formatMessage(messages.edit)}
          title={intl.formatMessage(messages.edit)}
        >
          <Icon name={pencilSVG} size="20px" />
        </Button>
        <Button
          basic
          icon
          aria-label={intl.formatMessage(messages.test)}
          title={intl.formatMessage(messages.test)}
          onClick={() => onTest(provider)}
        >
          <Icon name={worldSVG} size="20px" />
        </Button>
        <Button
          basic
          icon
          data-action="delete"
          aria-label={intl.formatMessage(messages.delete)}
          title={intl.formatMessage(messages.delete)}
          onClick={() => onDelete(provider)}
        >
          <Icon name={deleteSVG} size="20px" />
        </Button>
      </td>
    </tr>
  );
};

/** A row that drags by its handle. */
const SortableRow = ({
  libraries,
  ...props
}: RowProps & { libraries: Libraries }) => {
  const intl = useIntl();
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = libraries.dndKitSortable.useSortable({ id: props.provider.id });
  const label = intl.formatMessage(messages.move, {
    title: props.provider.title || props.provider.id,
  });
  return (
    <ProviderRow
      {...props}
      rowRef={setNodeRef}
      // Translate rather than Transform: a row stretched to the height of
      // the one it passes over reads as a glitch.
      style={{
        transform: libraries.dndKitUtilities.CSS.Translate.toString(transform),
        transition,
      }}
      dragging={isDragging}
      handle={
        <button
          type="button"
          ref={setActivatorNodeRef}
          {...attributes}
          {...listeners}
          className="identity-controlpanel__handle"
          aria-label={label}
          title={label}
        >
          <Icon name={dragSVG} size="20px" />
        </button>
      }
    />
  );
};

/** The rows, once the drag library has loaded. */
const SortableTable = ({
  libraries,
  providers,
  onReorder,
  ...rowProps
}: Props & { libraries: Libraries }) => {
  const {
    DndContext,
    KeyboardSensor,
    PointerSensor,
    closestCenter,
    useSensor,
    useSensors,
  } = libraries.dndKitCore;
  const {
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
  } = libraries.dndKitSortable;
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );
  const ids = providers.map((provider) => provider.id);
  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={({ active, over }: { active: any; over: any }) => {
        const next = movedIds(
          ids,
          String(active.id),
          over ? String(over.id) : null,
        );
        // A drop that changes nothing saves nothing.
        if (next) {
          onReorder(next);
        }
      }}
    >
      <SortableContext items={ids} strategy={verticalListSortingStrategy}>
        <Frame>
          {providers.map((provider) => (
            <SortableRow
              key={provider['@id']}
              libraries={libraries}
              provider={provider}
              {...rowProps}
            />
          ))}
        </Frame>
      </SortableContext>
    </DndContext>
  );
};

const ProvidersTable = ({ providers, onReorder, onTest, onDelete }: Props) => {
  const libraries: Libraries = useLazyLibs(DND_LIBRARIES);
  const ready = DND_LIBRARIES.every((name) => libraries[name]);

  if (ready) {
    return (
      <SortableTable
        libraries={libraries}
        providers={providers}
        onReorder={onReorder}
        onTest={onTest}
        onDelete={onDelete}
      />
    );
  }
  return (
    <Frame>
      {providers.map((provider) => (
        <ProviderRow
          key={provider['@id']}
          provider={provider}
          onTest={onTest}
          onDelete={onDelete}
        />
      ))}
    </Frame>
  );
};

export default ProvidersTable;
