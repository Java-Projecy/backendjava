package com.elecciones.backend.service;

import com.elecciones.backend.model.Candidato;
import com.elecciones.backend.repository.CandidatoRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class CandidatoService {

    private final CandidatoRepository candidatoRepository;

    public CandidatoService(CandidatoRepository candidatoRepository) {
        this.candidatoRepository = candidatoRepository;
    }

    public List<Candidato> getAll() {
        return candidatoRepository.findAll();
    }

    public Optional<Candidato> getById(UUID id) {
        return candidatoRepository.findById(id);
    }

    public Candidato save(Candidato candidato) {
        return candidatoRepository.save(candidato);
    }

    public void delete(UUID id) {
        candidatoRepository.deleteById(id);
    }
}
