import clsx from 'clsx';
import Heading from '@theme/Heading';
import { FaLock, FaBuilding, FaPython, FaBolt, FaLayerGroup, FaVial } from 'react-icons/fa';
import styles from './styles.module.css';

const FeatureList = [
  {
    title: 'Database-level security',
    icon: <FaLock />,
    description:
      'RLS is enforced by PostgreSQL itself — even raw SQL or a forgotten filter cannot leak another tenant’s rows.',
  },
  {
    title: 'Tenant & user policies',
    icon: <FaBuilding />,
    description:
      'TenantPolicy, UserPolicy, CustomPolicy, and the Pythonic ExpressionPolicy, mirroring django-rls.',
  },
  {
    title: 'Pool-safe context',
    icon: <FaBolt />,
    description:
      'Context is set per transaction via set_config(..., is_local=true), so it can never leak across pooled connections.',
  },
  {
    title: 'ORM-agnostic',
    icon: <FaPython />,
    description:
      'Binds at the SQLAlchemy engine layer — works with bare SQLAlchemy Core or Flask-SQLAlchemy.',
  },
  {
    title: 'Alembic migrations',
    icon: <FaLayerGroup />,
    description:
      'First-class migration operations: op.enable_rls, op.force_rls, op.create_policy, and more.',
  },
  {
    title: 'Proven against PostgreSQL',
    icon: <FaVial />,
    description:
      'Isolation, fail-closed behavior, and the FORCE/owner-bypass gotcha are verified against a live database.',
  },
];

function Feature({ icon, title, description }) {
  return (
    <div className={clsx('col col--4')}>
      <div className={styles.feature}>
        <div className={styles.featureIcon}>{icon}</div>
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
