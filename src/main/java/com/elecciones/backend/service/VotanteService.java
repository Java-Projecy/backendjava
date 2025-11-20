package com.elecciones.backend.service;

import com.elecciones.backend.model.Votante;
import com.elecciones.backend.repository.VotanteRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class VotanteService {

    private final VotanteRepository votanteRepository;

    public VotanteService(VotanteRepository votanteRepository) {
        this.votanteRepository = votanteRepository;
    }

    public List<Votante> getAll() {
        return votanteRepository.findAll();
    }

    public Optional<Votante> getById(UUID id) {
        return votanteRepository.findById(id);
    }

    public Optional<Votante> getByDni(String dni) {
        Votante votante = votanteRepository.findByDni(dni);
        return Optional.ofNullable(votante);
    }

    public Votante save(Votante votante) {
        return votanteRepository.save(votante);
    }

    public void delete(UUID id) {
        votanteRepository.deleteById(id);
    }
}
