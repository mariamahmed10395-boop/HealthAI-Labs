// src/pages/Contact/index.jsx
import Layout from "../../components/Layout";
import { fetchContact } from "../../api";
import { useQuery } from '@tanstack/react-query';
import { ExternalLink, Github } from 'lucide-react';

import abdullahImg from '../../assets/abdullah.jpeg';
import omarImg from '../../assets/omar.jpg';
import mohamedImg from '../../assets/mohamed.jpg';
import mariamImg from '../../assets/mariam.jpg';

const team = [
  {
    name: 'Abdullah Sameh',
    role: 'DevOps Engineer',
    url: 'https://abdullahsameh.qzz.io/',
    img: abdullahImg,
  },
  {
    name: 'Omar AlDujawy',
    role: 'ML Engineer',
    url: 'https://www.linkedin.com/in/omar-aldujawy-b10a9032a/',
    img: omarImg,
  },
  {
    name: 'Mohamed Mamdouh',
    role: 'AI Engineer',
    url: 'https://www.linkedin.com/in/ai-mohamed-mamdouh-74043b331/',
    img: mohamedImg,
  },
  {
    name: 'Mariam Ahmed',
    role: 'ML Engineer',
    url: 'https://mariamahmed10395-boop.github.io/portofolio/',
    img: mariamImg,
  },
];

export default function ContactPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['contact'],
    queryFn: fetchContact,
    retry: 1,
  });

  return (
    <Layout>
      {/* Hero */}
      <section className="pt-32 pb-16 bg-gradient-to-br from-blue-50 via-white to-purple-50 text-center px-4">
        <span className="inline-block bg-blue-100 text-blue-600 text-xs font-semibold tracking-widest uppercase px-4 py-1.5 rounded-full mb-4">
          Contact Us
        </span>
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
          Get in <span className="text-blue-600">Touch</span>
        </h1>
        <p className="text-gray-500 max-w-xl mx-auto text-lg">
          HealthAI Labs is an open-source project. Explore the code, open issues, or contribute on GitHub.
        </p>

        {/* Repo Link */}
        <a
          href="https://github.com/co-op-projects-to-boost-my-experience/HealthAI-Labs"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 mt-8 px-6 py-3 bg-gray-900 hover:bg-gray-800 text-white font-semibold rounded-xl shadow-lg hover:shadow-gray-400/30 transition"
        >
          <Github className="w-5 h-5" />
          View on GitHub
        </a>
      </section>

      {/* Team Section */}
      <section className="py-24 px-4 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <span className="inline-block bg-blue-100 text-blue-600 text-xs font-semibold tracking-widest uppercase px-4 py-1.5 rounded-full mb-4">
              The Team
            </span>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900">
              Meet the <span className="text-blue-600">Contributors</span>
            </h2>
            <p className="text-gray-500 mt-3 max-w-lg mx-auto">
              The people who built HealthAI Labs.
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-10">
            {team.map((member) => (
              <a
                key={member.name}
                href={member.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex flex-col items-center text-center"
              >
                <div className="relative mb-4">
                  <div className="w-28 h-28 rounded-2xl overflow-hidden ring-2 ring-transparent group-hover:ring-blue-400 transition-all duration-300 shadow-md group-hover:shadow-blue-200 group-hover:shadow-lg">
                    <img
                      src={member.img}
                      alt={member.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  </div>
                  <div className="absolute -bottom-2 -right-2 w-7 h-7 bg-blue-600 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 shadow">
                    <ExternalLink className="w-3.5 h-3.5 text-white" />
                  </div>
                </div>

                <p className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors duration-200">
                  {member.name}
                </p>
                <p className="text-xs text-blue-500 font-medium mt-0.5">{member.role}</p>
              </a>
            ))}
          </div>
        </div>
      </section>
    </Layout>
  );
}
