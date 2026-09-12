/**
 * The blocks this add-on offers.
 * @module config/blocks
 */
import type { ConfigType } from '@plone/registry';
import IdentitySignInBlockInfo, {
  SIGN_IN_BLOCK,
} from '../components/Blocks/SignIn';

/** The blocks offered inside a grid as well as on their own. */
const GRID_BLOCKS = [SIGN_IN_BLOCK];

export default function install(config: ConfigType) {
  config.blocks.blocksConfig[SIGN_IN_BLOCK] = IdentitySignInBlockInfo;

  // Offered inside a grid too. A project may have removed the grid block, so
  // finding none is not an error.
  const gridBlock = (config.blocks.blocksConfig as any).gridBlock;
  if (gridBlock?.allowedBlocks) {
    gridBlock.allowedBlocks = [
      ...gridBlock.allowedBlocks,
      ...GRID_BLOCKS.filter((id) => !gridBlock.allowedBlocks.includes(id)),
    ];
  }

  // The grid renders its children from its own `blocksConfig` when it has
  // one, and from the global one when it has not -- never from both. So a
  // grid with its own gets these blocks added to it, and one without is left
  // without: creating one here, holding only these, would take slate, images
  // and every other block out of every grid.
  if (gridBlock?.blocksConfig) {
    gridBlock.blocksConfig = {
      ...gridBlock.blocksConfig,
      ...Object.fromEntries(
        GRID_BLOCKS.map((id) => [id, config.blocks.blocksConfig[id]]),
      ),
    };
  }
  return config;
}
